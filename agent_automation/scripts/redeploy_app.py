#!/usr/bin/env python3
"""Stop and start a Domino app via the Chrome DevTools Protocol.

Drives the same running Chrome instance the agent uses (launched with
--remote-debugging-port=9222 via launch_chrome.sh). Operator must be
logged into Domino in that Chrome profile.

Usage:
    python3 redeploy_app.py
    python3 redeploy_app.py --url <overview_url>
    python3 redeploy_app.py --port 9222

Exits non-zero if any step times out or a required UI element is missing.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

try:
    from websocket import create_connection
except ImportError:
    sys.stderr.write(
        "Missing dependency: websocket-client. Install with:\n"
        "    pip install websocket-client\n"
    )
    sys.exit(2)


DEFAULT_URL = (
    "https://biraadoc126819.engineering-dev.domino.tech/"
    "u/integration-test/autodocs/apps/"
    "6a0cad5f8aa6aa0965406e75/latest/details/overview"
)
DEFAULT_PORT = 9222
STATUS_SEL = '[data-test="apps-details-subheader-status-tag"]'
MENU_SEL = '[data-test="apps-details-page-actions-more-actions-menu-trigger"]'
STOP_SEL = '[data-test="app-run-control-stop"]'
START_SEL = '[data-test="app-run-control-start"]'

# Per-transition wait, generous to cover cold starts.
TRANSITION_TIMEOUT_S = 180
POLL_INTERVAL_S = 2.0


class CDPSession:
    def __init__(self, port: int):
        self.port = port
        self._next_id = 0
        self._ws = self._connect()

    def _connect(self):
        tabs = json.loads(
            urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/json", timeout=5
            ).read()
        )
        page_tabs = [t for t in tabs if t.get("type") == "page"]
        if not page_tabs:
            raise RuntimeError("No page tabs found in Chrome")
        ws_url = page_tabs[0]["webSocketDebuggerUrl"]
        return create_connection(ws_url)

    def call(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        msg = {"id": self._next_id, "method": method, "params": params or {}}
        self._ws.send(json.dumps(msg))
        while True:
            resp = json.loads(self._ws.recv())
            if resp.get("id") == self._next_id:
                if "error" in resp:
                    raise RuntimeError(f"CDP error: {resp['error']}")
                return resp.get("result", {})

    def eval_js(self, expr: str):
        res = self.call(
            "Runtime.evaluate",
            {"expression": expr, "returnByValue": True, "awaitPromise": True},
        )
        if res.get("exceptionDetails"):
            raise RuntimeError(
                f"JS error: {res['exceptionDetails'].get('text')}"
            )
        return (res.get("result") or {}).get("value")

    def navigate(self, url: str) -> None:
        self.call("Page.enable")
        self.call("Page.navigate", {"url": url})
        # Wait for load by polling document.readyState.
        deadline = time.time() + 30
        while time.time() < deadline:
            state = self.eval_js("document.readyState")
            if state == "complete":
                return
            time.sleep(0.5)
        raise TimeoutError("page load timed out")


def status_text(cdp: CDPSession) -> str | None:
    return cdp.eval_js(
        f"(document.querySelector('{STATUS_SEL}') || {{}}).innerText || null"
    )


def wait_for_status(cdp: CDPSession, target: str) -> None:
    deadline = time.time() + TRANSITION_TIMEOUT_S
    while time.time() < deadline:
        current = (status_text(cdp) or "").strip()
        print(f"  status: {current!r}")
        if current == target:
            return
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"status never reached {target!r}")


def click(cdp: CDPSession, selector: str) -> None:
    ok = cdp.eval_js(
        f"(() => {{ const el = document.querySelector({selector!r}); "
        f"if (!el) return false; el.click(); return true; }})()"
    )
    if not ok:
        raise RuntimeError(f"element not found: {selector}")


def wait_for_visible(cdp: CDPSession, selector: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        ok = cdp.eval_js(
            f"!!document.querySelector({selector!r})"
        )
        if ok:
            return
        time.sleep(0.3)
    raise TimeoutError(f"selector did not appear: {selector}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="Overview URL")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="CDP port")
    args = parser.parse_args()

    cdp = CDPSession(args.port)
    print(f"connected to Chrome on port {args.port}")

    print(f"navigating to {args.url}")
    cdp.navigate(args.url)
    wait_for_visible(cdp, STATUS_SEL)

    current = (status_text(cdp) or "").strip()
    print(f"initial status: {current!r}")

    if current == "Running":
        print("stopping...")
        click(cdp, MENU_SEL)
        wait_for_visible(cdp, STOP_SEL, timeout=5)
        click(cdp, STOP_SEL)
        wait_for_status(cdp, "Stopped")

    print("starting...")
    click(cdp, MENU_SEL)
    wait_for_visible(cdp, START_SEL, timeout=5)
    click(cdp, START_SEL)
    wait_for_status(cdp, "Running")

    print("done; app is Running")
    return 0


if __name__ == "__main__":
    sys.exit(main())
