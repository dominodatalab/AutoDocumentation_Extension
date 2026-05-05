# Redeploying the target Domino app

After pushing code, publish a new app version from the latest git commit and
deploy it. Do **not** use stop/start for routine redeploys.

**Polling:** Check every **5 seconds** until the step completes or hits timeout. One `sleep 5` + one status read per cycle. No batched `for ... sleep 5` loops.

## Cluster and URLs (biradocg128969)

| What | Value |
|------|--------|
| Cluster host | `https://biradocg128969.engineering-dev.domino.tech` |
| Global app name | `modeldocs-ext1` |
| Global app id (overview) | `6a21ca684abe4b0b37ab1508` |
| Runtime app UUID (studio) | `6e8e4f7c-812e-4145-abd3-c3d4095a011b` |
| Git host project | `integration-test/modeldoc` (repo branch pin on overview) |
| Target project (generate) | `integration-test/modeldocs-target-bgp` |
| Target `projectId` | `6a21c81b3bff9f0d3ae561b1` |
| Branch pin | `ddl-bira-ignacio.governance` (unless app config changed) |

URLs:

- App overview (publish/deploy): `/global-apps/6a21ca684abe4b0b37ab1508/latest/details/overview`
- Target project overview: `/u/integration-test/modeldocs-target-bgp/overview`

**Model Docs studio (only E2E / browser test entry point):**

    https://biradocg128969.engineering-dev.domino.tech/apps/6e8e4f7c-812e-4145-abd3-c3d4095a011b?projectId=6a21c81b3bff9f0d3ae561b1

Do **not** use project extension iframes (`/u/.../extension?mountPointType=...`) for deploy smoke or generate tests.

Optional query param for model-scoped UI checks (prefills Model names filter; does not change the base URL):

    ...&modelId=mlflow3-logged-and-registered1

Full redeploy overview example:

    https://biradocg128969.engineering-dev.domino.tech/global-apps/6a21ca684abe4b0b37ab1508/latest/details/overview

After publish, Domino may redirect the overview to a version-specific path
(`/global-apps/.../<versionId>/details/overview`). That is fine; stay on the
overview for deploy and commit gate.

## Authoritative selectors

Publish / deploy flow (overview **Code** card):

- `apps-details-overview-tab-files-card-header-edit-btn` - pen icon, opens edit wizard.
- `resolved-commit-picker-update-btn` - **Update to latest** (in the modal).
- `wizard-finish-button` (`data-testid`) - **Publish App Version**.
- `app-deploy-button` - **Deploy** on overview (after publish; opens deploy modal).
- `deploy-app-modalsubmit-button` - **Deploy App version** in the deploy modal (required; publish alone does not deploy).

Commit verification (gate):

- `apps-details-overview-tab-files-card-git-resolved-commit-value` - resolved commit SHA shown on overview.

Status (optional, after deploy):

- `apps-details-subheader-status-tag` - `Running` / `Stopped` / `Pending` / `Failed` / `Not deployed`.

Legacy stop/start (do not use for E2E unless publish/deploy is unavailable):

- `apps-details-page-actions-more-actions-menu-trigger`
- `app-run-control-stop`
- `app-run-control-start`

## Procedure

1. Navigate to the global app overview URL above (`/latest/`).
2. Wait for the page to load (overview tab, Code card visible, app name `modeldocs-ext1`).
3. Click `[data-test="apps-details-overview-tab-files-card-header-edit-btn"]`.
4. In the modal/wizard, click `[data-test="resolved-commit-picker-update-btn"]` (**Update to latest**).
5. Click `[data-testid="wizard-finish-button"]` (**Publish App Version**).
6. Click `[data-test="app-deploy-button"]` (**Deploy** on overview). This opens the **Deploy App version** modal.
7. In the modal, click `[data-test="deploy-app-modalsubmit-button"]` (**Deploy App version**). Do not stop after step 6; overview status stays **Not deployed** until this click.
8. Poll until deploy finishes: read status every **5s** (one read per cycle, not a batched shell loop). Timeout **180s**; expect `Running`.

```javascript
() => ({
  status: document.querySelector('[data-test="apps-details-subheader-status-tag"]')?.innerText?.trim() || null,
})
```
9. **Verify resolved commit** (required): read
   `[data-test="apps-details-overview-tab-files-card-git-resolved-commit-value"]`
   and confirm it equals the full SHA you pushed (`git rev-parse HEAD` after push).
   If it does not match, **fail the E2E run**; see `e2e_test_runbook.md` Step 2.3.

   The value in that span is whatever Domino resolved for this deploy. The gate
   always compares to **your** pushed commit from `git rev-parse HEAD` (or
   `origin/<branch>` after `git fetch`), never to an example or a previous run.

Example read:

```javascript
() => {
  const el = document.querySelector('[data-test="apps-details-overview-tab-files-card-git-resolved-commit-value"]');
  return { commit: el?.innerText?.trim() || null };
}
```

## What to do when a step fails

- Edit or **Update to latest** not found: confirm overview URL and Code card loaded; UI may have changed - stop and ask the operator.
- **Deploy** missing after publish: complete the wizard; check for validation errors in the modal.
- Status still **Not deployed** after clicking overview **Deploy**: confirm the deploy modal opened and you clicked `[data-test="deploy-app-modalsubmit-button"]`.
- Resolved commit still wrong after deploy: confirm push reached `origin`, branch pin on the app matches your branch, retry publish/deploy once; then fail the test.
- Any HTTP / auth error: re-log into Domino in the debug Chrome profile (`setup.md`).

## Helper script

`scripts/redeploy_app.py` still implements the **legacy** stop/start flow. It does not run the publish/deploy wizard yet. The agent uses Chrome MCP per the steps above.

## After deploy

Visit the Model Docs studio URL above and confirm it loads.

Expect header `Model Docs` and `integration-test/modeldocs-target-bgp`.

## Browser testing notes

### Two projects on g128969

- `integration-test/modeldoc` - git host for the global app; branch/commit shown on overview Code card.
- `integration-test/modeldocs-target-bgp` - target for generation (`projectId=6a21c81b3bff9f0d3ae561b1`). Jobs, artifacts, generated docs on DFS.
- App surface - `/apps/6e8e4f7c-812e-4145-abd3-c3d4095a011b/` (always add `?projectId=6a21c81b3bff9f0d3ae561b1` or you get "Project ID required").

Governance seed and bundle tests also use `modeldocs-target-bgp` (`how-to-governance.md`).

### Waiting for job completion

`wait_for(["SUCCEEDED"])` matches historical rows immediately. Prefer
`wait_for(["Documentation generated successfully"])` (post-completion banner), or
poll `GET /api/job-history?projectId=<pid>` for your run's status.

### Triggering a generation

1. App URL with `?projectId=6a21c81b3bff9f0d3ae561b1`.
2. Click a template card.
3. Click "Generate Documentation".
4. Wait for completion (banner or API).

### Preview (mammoth)

After success: `document.getElementById('doc-preview-content').innerText`, or click
`.history-preview-link` in a succeeded row. Backend: `GET /api/preview-doc?projectId=&runId=`.

## Reading job logs

When a job in the target project completes and you need to inspect its
stdout (e.g. confirm a new log line shipped, or read the output filename),
use this Domino API endpoint:

    https://biradocg128969.engineering-dev.domino.tech/v4/jobs/<job_id>/logsWithProblemSuggestions?logType=complete

`<job_id>` is the Domino hex job ID (24-hex, e.g.
`6a22cea783bcef2885296c2b`).

### How to get the job ID

The autodoc app stores jobs in its own job store with a UUID `job_id`, and
separately a Domino hex `domino_run_id` once the Domino job is submitted.
The logs endpoint requires the **Domino hex** ID, not the UUID. Ways to
get it:

1. **From the app's History drawer** (preferred): open the app,
   click History. Each row's "View" link points to
   `/u/integration-test/modeldocs-target-bgp/jobs/<hex>/logs` - the `<hex>`
   in the URL is what you want.

2. **From the Domino Jobs page**: navigate to
   `https://biradocg128969.engineering-dev.domino.tech/u/integration-test/modeldocs-target-bgp/jobs`.
   Click the most recent job row; the URL becomes
   `.../jobs/<hex>/logs?...`.

3. **From the autodoc job store API**: GET
   `/<app-base>/api/jobs` (or the SSE/status endpoint) - the response
   includes `domino_run_id` for each job. Useful when scripting.

4. **From a known UUID job**: GET the app's `/api/jobs/<uuid>` to read
   its `domino_run_id` field.

Jobs that have not yet been submitted to Domino (still queued in the
autodoc engine) have no `domino_run_id` yet - wait until the job starts
running.

The endpoint returns JSON. Parse it and filter on `logType === "stdout"`:

```js
const raw = JSON.parse(document.body.innerText);
const stdout = raw.logset.logContent
  .filter(e => e.logType === 'stdout')
  .map(e => e.log);
```

Notes:

- Only works after the job has finished. Earlier reads return partial or
  empty content.
- `raw.logset.isComplete` is `true` when all logs are flushed.
- `prepareoutput` entries are setup/git output, not your code's stdout.
- The job list page (`.../jobs/<job_id>/logs`) renders log groups
  collapsed; use the API URL instead of clicking through the UI.

## Legacy cluster (biradoc126819)

Older docs and `test_code_source_browser.md` reference `biradoc126819` /
`autodoc-target-gbp` / `integration-test/autodocs`. That layout is **not**
present on `biradocg128969`. Use the constants above for current E2E and
governance work unless an operator explicitly points you at 126819 again.
