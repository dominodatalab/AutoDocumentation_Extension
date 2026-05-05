# E2E test runbook: push, deploy, generate, confirm, preview

End-to-end procedure for validating AutoDocumentation changes on the engineering-dev
cluster. Intended for an agent with **chrome-devtools MCP** attached to Chrome on port
9222 (see `setup.md`).

**Polling:** Check status every **5 seconds**, not less often. One check per wait cycle.

**Do:** `sleep 5` (or MCP `evaluate_script` with 5s `setTimeout`) then read status; repeat until done or timeout.

**Do not:** batch waits in one shell loop, e.g. `for i in 1 2 3 ... 20; do sleep 5; done` then a single check. That skips intermediate states and wastes time when the job already finished.

**Do not:** one long sleep (e.g. `sleep 100`) or one `evaluate_script` that polls for 15+ minutes (MCP timeout).

## Constants (engineering-dev, biradocg128969)

| What | Value |
|------|--------|
| Cluster host | `https://biradocg128969.engineering-dev.domino.tech` |
| Global app name | `modeldocs-ext1` |
| Global app id (overview) | `6a21ca684abe4b0b37ab1508` |
| Runtime app UUID (studio) | `6e8e4f7c-812e-4145-abd3-c3d4095a011b` |
| Git host project | `integration-test/modeldoc` |
| Target project | `integration-test/modeldocs-target-bgp` |
| Target `projectId` | `6a21c81b3bff9f0d3ae561b1` |
| Branch pin | `ddl-bira-ignacio.governance` |

URLs:

- App overview (redeploy): `/global-apps/6a21ca684abe4b0b37ab1508/latest/details/overview`
- Target project overview: `/u/integration-test/modeldocs-target-bgp/overview`

**Model Docs studio (only entry point for Steps 2.4, 3, 4, 5, 6):**

    https://biradocg128969.engineering-dev.domino.tech/apps/6e8e4f7c-812e-4145-abd3-c3d4095a011b?projectId=6a21c81b3bff9f0d3ae561b1

Do **not** use `/u/.../extension?mountPointType=...` for E2E.

Optional: append `&modelId=<mlflow-registered-model-name>` to prefill the Model names filter when testing model-scoped behavior.

See `deploy.md` for full URLs and legacy `biradoc126819` notes.

## Reproducible checklist

1. Push branch; record `E2E_EXPECTED_COMMIT`.
2. Publish + deploy on global-apps overview; poll **Running** (5s interval).
3. Commit gate: overview Commit ID == `E2E_EXPECTED_COMMIT` (else **stop**).
4. Open Model Docs studio URL only; templates load.
5. Generate **Standard ML Model Doc**; poll success every 5s.
6. Confirm history **SUCCEEDED**, preview has content.

## Prerequisites

1. Chrome running with `--remote-debugging-port=9222` and Domino logged in (`setup.md`).
2. `chrome-devtools` MCP connected in Cursor (`/mcp` shows Connected).
3. Code changes committed on the branch the global app deploys (`ddl-bira-ignacio.governance` unless the app pin changed).
4. `make test` green before push (repo convention).
5. **Gate:** `apps-details-overview-tab-files-card-git-resolved-commit-value` must match pushed SHA before generation (Step 2.3). If not, **fail the run**; do not generate.

## Step 1: Push code

From repo root, on your feature branch (e.g. `ddl-bira-ignacio.governance`):

```bash
git status
git add <only files for this change>
git commit -m "<conventional commit message>"
git push -u origin HEAD
```

Verify push:

```bash
git status   # should not say "ahead of origin"
```

Record what E2E must match (run from repo root):

```bash
export E2E_EXPECTED_BRANCH=$(git rev-parse --abbrev-ref HEAD)
export E2E_EXPECTED_COMMIT=$(git rev-parse HEAD)
echo "branch=$E2E_EXPECTED_BRANCH commit=$E2E_EXPECTED_COMMIT"
```

Optional sanity check against remote:

```bash
git fetch origin
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/$E2E_EXPECTED_BRANCH)"
```

Redeploy uses **publish + deploy** on the overview (not stop/start). Step 2.4 verifies the resolved commit SHA after deploy.

**Do not** commit secrets, `autodoc-env/`, or local-only scripts unless intended.

## Step 2: Publish and deploy app (Chrome MCP)

Goal: point the **modeldocs-ext1** global app at the latest commit on your branch and deploy it. **Do not** use stop/start for this step.

See `deploy.md` for full detail.

### 2.1 Navigate

MCP: `navigate_page` → app overview URL (full URL in Constants).

Wait for the overview Files card (edit pen button visible).

### 2.2 Publish latest commit

In order:

1. Click `[data-test="apps-details-overview-tab-files-card-header-edit-btn"]` (Edit App / pen).
2. Click `[data-test="resolved-commit-picker-update-btn"]` (**Update to latest**).
3. Click `[data-testid="wizard-finish-button"]` (**Publish App Version**). Wait for the publish wizard/modal to close.
4. Click `[data-test="app-deploy-button"]` (**Deploy** on overview). This opens the **Deploy App version** modal.
5. Click `[data-test="deploy-app-modalsubmit-button"]` (**Deploy App version** in the modal). Required; do not treat step 4 alone as deployed.

Poll `[data-test="apps-details-subheader-status-tag"]` every **5s** (max) until `Running` (timeout 180s) after step 5.

If any control is missing or the wizard errors, stop and ask the operator.

### 2.3 Gate: verify resolved commit (required)

**Purpose:** Prove the app resolved the same git SHA you pushed. If this fails, **stop the E2E run** (do not run Step 4 Generate).

Read the resolved commit on the overview (after deploy, same overview URL):

```javascript
() => {
  const el = document.querySelector('[data-test="apps-details-overview-tab-files-card-git-resolved-commit-value"]');
  return { commit: el?.innerText?.trim() || null };
}
```

**Pass** only if `commit` equals `E2E_EXPECTED_COMMIT` from Step 1 (full 40-char SHA, same as `git rev-parse HEAD` after push). Any SHA you see in the UI (e.g. `ad27a54e67eb1fa1b33aaf347f37fd0aeb1486bc`) is only an example from a past run; the gate must match **this** push, not a documented or remembered hash.

**Poll** if empty or stale: read commit, compare, `sleep 5`, reload overview if still wrong. Timeout **120s**. One read per agent turn; do not batch sleeps.

Single read:

```javascript
() => {
  const el = document.querySelector('[data-test="apps-details-overview-tab-files-card-git-resolved-commit-value"]');
  return { commit: el?.innerText?.trim() || null };
}
```

**On failure:** E2E **FAILED**; do not generate.

**On success:** continue to Step 2.4.

### 2.4 Smoke check

`navigate_page` → Model Docs studio URL with `projectId`.

`wait_for` text: `Choose a template` or `Model Docs`.

Optional: wait for `Standard ML Model Doc` after templates load.

## Step 3: Open Model Docs (app URL)

Use only:

`https://biradocg128969.engineering-dev.domino.tech/apps/6e8e4f7c-812e-4145-abd3-c3d4095a011b?projectId=6a21c81b3bff9f0d3ae561b1`

Optional: `&modelId=<name>` for model-scoped checks.

MCP: `navigate_page` → that URL.

Confirm:

- Header shows `Model Docs` and `integration-test/modeldocs-target-bgp`
- Template gallery loads (not stuck on "Loading templates...")

## Step 4: Generate documentation

### 4.1 Select a template

Click the template card for **Standard ML Model Doc** (default E2E template):

```javascript
() => {
  const cards = Array.from(document.querySelectorAll('.template-card'));
  const card = cards.find((c) => (c.querySelector('.template-card-name')?.innerText || '').includes('Standard ML Model Doc'));
  if (!card) return { ok: false, names: cards.map((c) => c.querySelector('.template-card-name')?.innerText) };
  card.click();
  return { ok: true, selected: card.querySelector('.template-card-name')?.innerText };
}
```

Verify `#generate-btn` is enabled:

```javascript
() => {
  const btn = document.getElementById('generate-btn');
  return { disabled: btn?.disabled, text: btn?.innerText?.trim() };
}
```

### 4.2 Start generation

```javascript
() => {
  const btn = document.getElementById('generate-btn');
  if (!btn || btn.disabled) return { ok: false, disabled: btn?.disabled };
  btn.click();
  return { ok: true };
}
```

Expect UI: results panel shows "Submitting job..." then job progress.

### 4.3 Wait for completion

**Do not** use `wait_for(["SUCCEEDED"])` alone; history rows already contain SUCCEEDED.

**Agent loop** (timeout 20 minutes): run the single-check snippet below; if not terminal, `sleep 5`, repeat. Do not use one long `evaluate_script` loop or batched shell `for ... sleep 5`.

Single check:

```javascript
() => {
  const success = document.querySelector('.results-success-headline');
  if (success?.innerText?.includes('Documentation generated successfully')) {
    return { done: true, ok: true, state: 'success', headline: success.innerText.trim() };
  }
  const failed = document.querySelector('.results-failed-headline');
  if (failed) {
    const detail = document.querySelector('.results-failed-detail')?.innerText?.trim();
    return { done: true, ok: false, state: 'failed', headline: failed.innerText.trim(), detail };
  }
  const row = document.querySelector('tr[data-run-id]');
  return {
    done: false,
    submitting: document.querySelector('.results-submitting-text')?.innerText?.trim() || null,
    topRunId: row?.getAttribute('data-run-id') || null,
    topRow: row?.innerText?.replace(/\s+/g, ' ').trim().slice(0, 120) || null,
  };
}
```

Alternate (API): use the app-prefixed path (relative fetch from the studio page):

```javascript
async () => {
  const pid = '6a21c81b3bff9f0d3ae561b1';
  const base = (window.location.pathname.match(/^(\/apps[^/]*\/[^/]+)/i) || [])[1] + '/';
  const r = await fetch(base + 'api/job-history?projectId=' + encodeURIComponent(pid));
  const text = await r.text();
  try {
    const data = JSON.parse(text);
    const jobs = data.jobs || [];
    return { ok: r.ok, newest: jobs[0] || null };
  } catch (e) {
    return { ok: false, parseError: String(e), bodyStart: text.slice(0, 120) };
  }
}
```

**Agent note:** Generation can take many minutes. Loop: **check state → if not done, sleep 5s → check again**. Separate MCP turns are fine; batched `for ... sleep 5` loops are not.

## Step 5: Confirm document was generated

### 5.1 In-app success UI

Success banner present (see 4.3).

### 5.2 History row

Open History if not visible (button text `History`). Top row should be **SUCCEEDED** with a recent timestamp and links **Open** / **Preview** / **View**.

Capture newest `data-run-id` from the first succeeded row:

```javascript
() => {
  const row = document.querySelector('tr[data-run-id]');
  const statusCell = row ? row.querySelector('td:nth-child(2)') : null;
  return {
    runId: row?.getAttribute('data-run-id') || null,
    status: statusCell?.innerText?.trim() || null,
  };
}
```

### 5.3 Optional: Domino job logs

From the row's "View" link, extract hex job id from URL
`/jobs/integration-test/modeldocs-target-bgp/<hex>/logs`.

After job completes:

`GET /v4/jobs/<hex>/logsWithProblemSuggestions?logType=complete`

Filter `logType === "stdout"` for CLI output (see `deploy.md`).

## Step 6: Preview document

### 6.1 Automatic preview (after success)

Right panel should load mammoth HTML. Check:

```javascript
() => {
  const el = document.getElementById('doc-preview-content');
  const err = document.getElementById('doc-preview-error');
  const loading = document.getElementById('doc-preview-loading');
  const text = (el?.innerText || '').trim();
  return {
    hasContent: text.length > 100,
    previewChars: text.length,
    previewStart: text.slice(0, 200),
    errorVisible: !!(err && err.offsetParent !== null),
    loadingVisible: !!(loading && loading.offsetParent !== null),
  };
}
```

Pass if `hasContent` is true and text mentions expected section titles (e.g. "Executive Summary").

### 6.2 History preview link

```javascript
() => {
  const link = document.querySelector('.history-preview-link');
  if (!link) return { ok: false };
  link.click();
  return { ok: true, runId: link.getAttribute('data-run-id') };
}
```

Wait for modal / panel with document text or error.

### 6.3 API (debug)

`GET /api/preview-doc?projectId=6a21c81b3bff9f0d3ae561b1&runId=<full_run_id>`

Server uses `runId[:8]` to load `docs/<short>/model_docs.docx` from target project DFS.

## Failure handling

| Symptom | Action |
|---------|--------|
| **Resolved commit mismatch** (`git-resolved-commit-value` != pushed SHA) | **FAIL E2E**; do not generate. Re-run Step 2.2 publish/deploy or fix branch pin |
| MCP cannot connect | Start Chrome with port 9222; check `setup.md` |
| Project ID required | Add `?projectId=6a21c81b3bff9f0d3ae561b1` |
| Generate disabled | Select a template first |
| Submission failed | Read `.results-failed-detail`; check app logs / API |
| Timeout waiting for success | Check Domino job logs; ask operator |
| Preview empty / error | Network tab `preview-doc`; 404 = missing docx on DFS |

When a step fails during an agent run: **stop, report what was observed, ask the operator** before retrying blindly.

## Validated run (2026-06-05, biradocg128969)

| Step | Result |
|------|--------|
| Push | `759d266` on `ddl-bira-ignacio.governance` (A0 fixtures) |
| Commit gate | **PASS** — overview `759d266f4da6aaa803fd0f2089188e3daaf5d1dc` |
| Publish/deploy | global-apps overview → v2.0 → Deploy modal → **Running** |
| Studio | App URL loads; `integration-test/modeldocs-target-bgp` |
| Generate | Standard ML Model Doc; success banner |
| New run | `data-run-id=6a22cea783bcef2885296c2b`, submitted 06/05/26 09:27 |
| Auto preview | `doc-preview-content` ~92k chars, includes Executive Summary |

## Validated run (2026-06-02, biradoc126819, legacy)

| Step | Result |
|------|--------|
| Push | Skipped: branch already synced with `origin` |
| Commit gate | **Not run** on that date; resolved commit lagged push |
| Deploy | Legacy stop/start only (superseded by publish/deploy wizard) |
| Studio | Loaded, templates OK |
| Generate | Standard ML Model Doc; success banner |
| New run | `data-run-id=6a1f22ebdb2cc52c9ed2b9f5`, submitted 06/02/26 14:37 |
| Auto preview | `doc-preview-content` ~33k chars, includes Executive Summary |

## Run log template

Copy for each run:

```
Date:
Branch / commit pushed (git rev-parse):
Commit gate Step 2.3: PASS / FAIL (expected SHA vs git-resolved-commit-value)
Publish/deploy: edit -> Update to latest -> Publish -> Deploy overview -> Deploy App version modal (Y/N)
Studio loads: Y/N
Template:
Generation: success / failed / timeout / SKIPPED (gate failed)
Newest data-run-id:
Preview hasContent: Y/N (first 200 chars)
Notes:
```
