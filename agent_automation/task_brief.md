# Task brief and agreed scope

This document captures the original task directions, the agent's clarifying
questions, and the user's answers. It is the source of truth for what the
agent is and is not allowed to do on this work.

## 1. Original directions from user

We need to make some complex code changes, bringing code that affects UI and
UI only from the branch `felix-ui-improvements` into
`ddl-bira-ignacio.ui_overhaul`.

Constraints:

- Only the UI in `ddl-bira-ignacio.ui_overhaul` is to be modified.
- There could be UI and UI functionality (like field names, defaults, etc.)
  in `ddl-bira-ignacio.ui_overhaul` that need to stay untouched and might
  have been changed in `felix-ui-improvements`.
- In such cases and any case where the work is not trivial, the agent must
  stop and ask how to proceed.
- The `details` HTML element with `class="adv-opts-accordion"` in
  `felix-ui-improvements` is to be ignored and not ported over.
- Reference URL for current `ddl-bira-ignacio.ui_overhaul` deployment:
  `https://biraadoc126819.engineering-dev.domino.tech/apps/ae9683eb-bbec-437b-b7b7-195df75daa4d?projectId=6a0caee08aa6aa0965406e83`
- Reference URL for `felix-ui-improvements` deployment:
  `https://biraadoc126819.engineering-dev.domino.tech/apps/7f8d4371-5e07-449a-9d23-311cf7869f14/?projectId=6a0caee08aa6aa0965406e83`
- Never change `felix-ui-improvements`. Read-only.
- After making code changes to `ddl-bira-ignacio.ui_overhaul`, commit with a
  simple but clear message (no signature), push, then deploy via:
  a. Visit
     `https://biraadoc126819.engineering-dev.domino.tech/u/integration-test/autodocs/apps/6a0cad5f8aa6aa0965406e75/latest/details/overview`
     (the `/latest/` segment is important - the previous-run URL with a
     concrete run id may not show the more-actions menu)
  b. Click `data-test="apps-details-page-actions-more-actions-menu-trigger"`,
     then click `data-test="app-run-control-stop"` in the menu.
  c. Read the `data-test="apps-details-subheader-status-tag"` span and wait
     until it says "Stopped".
  d. Click the more-actions-menu-trigger again, then click
     `data-test="app-run-control-start"`.
  e. Read the status tag and wait until it says "Running".
  f. If any of these steps fail, stop and ask for instructions.
- After changes, visit both apps and confirm
  `ddl-bira-ignacio.ui_overhaul` looks like `felix-ui-improvements`
  (visual only).
- Write these steps to a doc in this dir, in a subdir called
  `agent_automation`. Write Python scripts to help with these steps if
  needed.

## 2. Clarifying questions and user answers

### Q: How will the agent "see" the deployed apps?

A: Install and use the `chrome-devtools` MCP integration. User authenticates
in Chrome the first time; the session is reused afterwards.

### Q: Which Chrome MCP server?

A: `chrome-devtools-mcp` (attaches to a running Chrome with remote
debugging on port 9222).

### Q: Scope of "UI" - HTML/CSS only, or also Python?

A: This is a Python app. UI lives mostly in `auto_model_docs/studio/` and
spans HTML, CSS, and some `.py` files. The most important thing is to keep
the code the UI calls working, and any API call the UI makes must have the
same payload, shape, and values.

### Q: Which files are the source of changes to port?

A: Just the changes in commit `2dba8c393b65997d3ac24530db9a3c8d30188c99`
on `felix-ui-improvements`.

### Q: What is the state of the working tree?

A: `ddl-bira-ignacio.ui_overhaul` is checked out and ready. The following
untracked files must be left alone:

    .sesskey
    TODO.md
    auto_model_docs/autodoc-env/
    auto_model_docs/run_cli_local.sh

### Q: How many commits?

A: Split into a few logical commits, 3-4 max so gradual changes are
visible without being too granular.

### Q: Tests?

A: `make test` must pass before each commit. User confirmed all tests are
green and not flaky as of session start.

### Q: Behavior when porting non-UI Python files (routes, state, job
engine)?

A: Port freely in UI-only files. If something referenced in `felix` does
not exist in `ddl-bira-ignacio.ui_overhaul`, it was likely intentionally
removed - stop and ask rather than re-adding.

### Q: Commit message style?

A: Conventional Commits. No `Co-Authored-By` or other signature lines.

### Q: GitHub operations?

A: Use the `gh` CLI for any GitHub operations.

### Q: What about `class="adv-opts-accordion"`?

A: That `details` element exists only in `felix-ui-improvements`. Treat it
as if it did not exist there. Never port it. Never add it.

### Q: Should the agent fetch latest from origin first?

A: No. Everything local is up to date.

### Q: Rollback if deploy fails?

A: Stop and ask the user. Do not improvise.

### Q: Should `auto_model_docs/autodoc-env/` (a venv) be touched?

A: Leave it alone.

### Q: Order of work?

A: Agreed sequence:

0. Inspect the existing target branch code and the deployed
   `ddl-bira-ignacio.ui_overhaul` UI in the browser first.
1. Enumerate every file/hunk in felix commit `2dba8c39`.
2. For each change, diff against current target branch state.
3. View both deployed apps for visual reference.
4. Stop-and-ask on every ambiguity (intentional removals, functional
   code, default-value changes, payload-affecting changes).
5. Make changes in 3-4 logical commits; run `make test` before each.
6. Push via `gh`/`git`. Run the documented stop/start deploy flow.
7. Re-visit both apps and confirm visual parity.

### Q: Where do the docs and helper scripts live?

A: `agent_automation/` at the repo root.

## 3. Outstanding questions / open items

None at session start. Any new ambiguity discovered during the diff phase
will be raised as a stop-and-ask before code is written.

## 4. Common pitfalls when driving the app

### Three projects, not one

The autodoc deployment involves three distinct Domino projects. They are
easy to confuse:

- `autodocs` - hosts the running app pod. URLs under
  `/u/integration-test/autodocs/...` and `/apps/<app-uuid>/details/...`
  refer to the app host. Used only for stop/start/redeploy.
- `autodoc-target-gbp` - the test target project the app generates
  documentation for. Its project id is `6a0caee08aa6aa0965406e83`. Job
  history, artifacts, and the `/dfs/code` browser all live here.
- `app-uuid` - the deployed app surface itself
  (`/apps/ae9683eb-bbec-437b-b7b7-195df75daa4d/`). This is what the user
  actually clicks through.

### The app URL needs `?projectId=...`

Navigating to `https://.../apps/<app-uuid>/` without a `projectId` query
parameter shows a hard error: "Project ID required". Always append
`?projectId=6a0caee08aa6aa0965406e83` (the target project id). The brief's
section 1 URLs already include it - do not strip it.

### `wait_for` matches against the entire page

The chrome MCP `wait_for(text=[...])` returns the moment the text appears
anywhere on the page. The history table renders rows like `SUCCEEDED`,
`FAILED`, `PENDING` for past jobs, so `wait_for(["SUCCEEDED"])` returns
immediately even if your new job is still pending.

Best fix: wait for the in-app success banner. Once the job completes
and the UI re-renders, an element appears in the DOM:

    <div class="results-success-headline">Documentation generated successfully</div>

This text is unique to the post-completion view (not present in
historical rows), so `wait_for(["Documentation generated successfully"])`
is safe.

Alternatively, hit the job-history API directly:
`GET /api/job-history?projectId=<pid>` returns the job list as JSON,
including each job's `domino_run_id` and `status`. Filter on your run id
and check `status === "succeeded"` / `"failed"`.

If you must read from the DOM and the banner isn't the right hook (e.g.
the History drawer is open instead), scope by `data-run-id`. Each
history row has `data-run-id="<domino_run_id>"`. The status is the
second `<td>` of that row:

    document.querySelector('tr[data-run-id="<id>"] td:nth-child(2)').innerText

### Triggering a generation

`deploy.md` covers stop/start. To actually run a generation through the
UI:

1. Navigate to the app URL with `?projectId=<target_project_id>`.
2. Click a template card (e.g. "Standard ML Model Doc").
3. Click "Generate Documentation".
4. Poll the first history row (or row with your `data-run-id`) for
   `SUCCEEDED` / `FAILED`.

### Verifying the in-app preview (mammoth)

The studio renders a mammoth-converted HTML preview of the generated
docx. There are two entry points:

**1. Automatic preview after generation.** After "Documentation
generated successfully" appears, the right-hand panel auto-loads the
preview for the just-completed job. Wait for the banner, then check the
DOM:

    document.getElementById('doc-preview-content').innerText

If it contains expected document content (e.g. "Executive Summary",
"Machine Learning Model Documentation"), mammoth rendering worked. If
`doc-preview-error` is visible or `doc-preview-loading` never clears,
the API failed - check `/api/preview-doc` in the network panel.

**2. Preview from the History drawer.** Each succeeded history row has
a `Preview` link with class `.history-preview-link` and a
`data-run-id="<domino_run_id>"` attribute. Click the link to open the
preview modal (heading "Document Preview"). Programmatically:

    document.querySelector('.history-preview-link').click()

Then wait for either the document text (e.g. "Executive Summary") or an
error.

Both paths call `GET /api/preview-doc?projectId=<pid>&runId=<full_run_id>`
on the server side. The server takes `runId[:8]`, fetches
`docs/<short>/model_docs.docx` from the target project's DFS via
`/u/<owner>/<project>/raw/latest/<path>`, and pipes it through mammoth.
A 404 means the file isn't at that path; a 500 means mammoth or auth
failed - check server logs.
