# Agent host setup

These steps make the Claude Code agent able to drive a real Chrome browser
against Domino app URLs. Done once per machine.

## 1. Install Node 20 via asdf

`chrome-devtools-mcp` requires Node 20.19+. macOS Homebrew `node@18` is too
old. We install Node 20 with asdf without disturbing the system Node.

    asdf plugin add nodejs
    asdf install nodejs 20.19.0
    asdf set -u nodejs 20.19.0

Verify the binary exists:

    ls ~/.asdf/installs/nodejs/20.19.0/bin/node

Note: on this machine `~/.zshrc` prepends `/opt/homebrew/opt/node@18/bin` to
PATH, so `node` on the shell may still report v18. That is intentional - the
MCP wrapper below pins Node 20 explicitly without touching shell PATH.

## 2. Wrapper script that pins Node 20 + Chrome URL

The MCP server is launched via this wrapper so it always uses Node 20 and
always attaches to a running Chrome at `http://127.0.0.1:9222`.

Path: `~/.local/bin/chrome-devtools-mcp-wrapper`

    #!/bin/bash
    export PATH="/Users/biraignacio/.asdf/installs/nodejs/20.19.0/bin:$PATH"
    exec /Users/biraignacio/.asdf/installs/nodejs/20.19.0/bin/npx \
        -y chrome-devtools-mcp@latest \
        --browserUrl http://127.0.0.1:9222 "$@"

Make it executable:

    chmod +x ~/.local/bin/chrome-devtools-mcp-wrapper

## 3. Register the MCP server with Claude Code

    claude mcp remove chrome-devtools 2>/dev/null
    claude mcp add chrome-devtools ~/.local/bin/chrome-devtools-mcp-wrapper

Verify:

    claude mcp list | grep chrome-devtools
    # chrome-devtools: ... - Connected

If status is "Failed to connect", it means Chrome is not running on port
9222 yet. Start it (next step) and try again.

## 4. Launch Chrome with remote debugging

The agent talks to Chrome via the DevTools protocol on port 9222. Chrome
must be launched with that flag.

Use the helper script:

    ./scripts/launch_chrome.sh

Or manually:

    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
        --remote-debugging-port=9222 \
        --user-data-dir="$HOME/chrome-debug-profile"

Important:

- Use a dedicated `--user-data-dir` so this Chrome does not clash with your
  normal browsing profile.
- The first time, log into Domino in this Chrome window. The session
  cookie is persisted in the dedicated profile and reused on subsequent
  launches.

## 5. Restart the Claude Code session

After registering or changing the MCP config, restart Claude Code so the
tool schemas reload. From within Claude Code you can use `/mcp` to verify
the server is connected.

## 6. Quick health check

Inside Claude Code, ask the agent to call `list_pages`. Expected output is
the currently open tabs in your debug Chrome window. If you see an error
like "Could not connect to Chrome", Chrome is not running with the
debugging flag - re-run step 4.
