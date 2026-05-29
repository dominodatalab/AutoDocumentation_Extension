# Redeploying the target Domino app

After pushing code to `ddl-bira-ignacio.ui_overhaul`, the running Domino app
needs to be cycled (stop / start) for the new code to take effect. This
document describes the exact procedure the agent follows, what each step
verifies, and what to do when something fails.

## Authoritative selectors

These are the `data-test` attributes the agent drives:

- `apps-details-page-actions-more-actions-menu-trigger` - the kebab/more
  button next to "Share" in the page actions area.
- `app-run-control-stop` - menu item that stops the running app.
- `app-run-control-start` - menu item that starts the stopped app.
- `apps-details-subheader-status-tag` - the status pill, contains the
  current state text: `Running` / `Stopped` / `Pending` / `Failed`.

## URL

Use the `/latest/` form of the URL so the page reflects the most recent run
of the app:

    https://biraadoc126819.engineering-dev.domino.tech/u/integration-test/autodocs/apps/6a0cad5f8aa6aa0965406e75/latest/details/overview

The previously documented URL pinned a concrete run id
(`.../6a104b399f6ccf361ad0e936/...`), which routes to a historical run and
does not always show the more-actions menu. The `/latest/` form is
session-stable.

## Procedure

1. Navigate to the `/latest/` overview URL above.
2. Wait until `apps-details-subheader-status-tag` text is `Running`,
   `Stopped`, `Pending`, or `Failed`. If `Pending`, keep waiting until it
   resolves to one of the others.
3. If status is `Running`:
   a. Click `apps-details-page-actions-more-actions-menu-trigger`.
   b. Click `app-run-control-stop`.
   c. Wait until the status tag reads `Stopped`.
4. Click `apps-details-page-actions-more-actions-menu-trigger`.
5. Click `app-run-control-start`.
6. Wait until the status tag reads `Running`.

Status transitions can take a minute or two each. The agent polls the
status tag with a 60-90 second timeout per transition.

## What to do when a step fails

- More-actions trigger not found: confirm the URL is the `/latest/` form
  and the page finished loading. If the trigger still does not exist, the
  Domino UI may have changed - stop and ask the operator.
- Status never reaches `Stopped` or `Running` within the timeout: do not
  retry blindly. Stop and ask the operator. The app may be wedged.
- Any HTTP / auth error: the Chrome session may have expired. Re-log into
  Domino in the dedicated debug Chrome profile (see `setup.md`).

## Helper script

`scripts/redeploy_app.py` automates steps 1-6 via the Chrome DevTools
Protocol against the same running Chrome instance the agent uses. It is
intended for manual operator use; the agent itself drives Chrome through
MCP tools.

## After the app is back up

Visit the target app URL and the felix reference URL side by side and
confirm visual parity:

- Target: `https://biraadoc126819.engineering-dev.domino.tech/apps/ae9683eb-bbec-437b-b7b7-195df75daa4d?projectId=6a0caee08aa6aa0965406e83`
- Felix:  `https://biraadoc126819.engineering-dev.domino.tech/apps/7f8d4371-5e07-449a-9d23-311cf7869f14/?projectId=6a0caee08aa6aa0965406e83`

## Reading job logs

When a job in the target project completes and you need to inspect its
stdout (e.g. confirm a new log line shipped, or read the output filename),
use this Domino API endpoint:

    https://biraadoc126819.engineering-dev.domino.tech/v4/jobs/<job_id>/logsWithProblemSuggestions?logType=complete

`<job_id>` is the Domino hex job ID (24-hex, e.g.
`6a10a5ec9f6ccf361ad0f1e0`).

### How to get the job ID

The autodoc app stores jobs in its own job store with a UUID `job_id`, and
separately a Domino hex `domino_run_id` once the Domino job is submitted.
The logs endpoint requires the **Domino hex** ID, not the UUID. Ways to
get it:

1. **From the app's History drawer** (preferred): open the autodoc app,
   click History. Each row's "Logs" link points to
   `/u/integration-test/autodoc-target-gbp/jobs/<hex>/logs` - the `<hex>`
   in the URL is what you want.

2. **From the Domino Jobs page**: navigate to
   `https://biraadoc126819.engineering-dev.domino.tech/u/integration-test/autodoc-target-gbp/jobs`.
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
