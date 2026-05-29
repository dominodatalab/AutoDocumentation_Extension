# Test plan: code source browser feature

## What was implemented

The "Browse spec files" modal shows datasets and the project's own code repo as sources.

- Source dropdown shows "Source code" first (no prefix, no path), then dataset names (no prefix)
- File browser fetches from `/api/code-files` for code, `/api/dataset-files` for datasets
- For code sources, only `.yaml`/`.yml` files are shown (dirs always shown)
- Selecting a file and confirming copies it to the autodoc dataset (same as before)
- File size display removed everywhere
- Label changed from "Dataset" to "Source"
- Loading indicator appears in file browse area while files are fetched

## Key architectural decisions

### Label changes
- Code source option: was `Git- /mnt/code` or `Code- /mnt`, now just `Source code`
- Dataset options: were `DS- <name>`, now just `<name>`
- Rationale: there is only ever one code source, so a prefix and path add no value

### GBP code source resolution (the bug and fix)

**Problem:** For GBP projects, `browseCode.projectSettings.repositories` and
`/v4/projects/{id}/gitRepositories` both only return **imported** repos, never the
project's own repo. The old fallback grabbed the first entry from `gitRepositories`,
which was always the wrong (imported) repo.

**Root cause discovery:** Added a debug endpoint `/api/debug-code-root` that called all
three APIs and logged their full responses. The `/v4/projects/{id}` response includes a
`mainRepository` field with the project's own repo ID. Neither `browseCode` nor
`gitRepositories` expose it.

**Fix:** `get_code_source_info` in `domino_client.py`:
- GBP (`isGitBasedProject == true`): call `/v4/projects/{id}`, use `project.mainRepository.id`
- DFS (`isGitBasedProject == false`): no repo ID needed, location is `/mnt`
- The `repositories` list from `browseCode` is never scanned — it only contains imported repos and is not useful for resolving the project's own code source

**GBP test project:** `integration-test/autodoc-target-gbp` (project ID `6a0caee08aa6aa0965406e83`)
- Main repo: `simple-demo` (repo ID `6a0caee28aa6aa0965406e86`)
- Imported repo: `AutoDocumentation_Extension` (repo ID `6a0f007d7bb8e6117d64ef66`) — this was the wrong one being used before the fix
- Expected root contents: `noop/`, `spec2/`, `listener.py`, `test-git1.yaml`

---

## GBP project test

Project: `https://biraadoc126819.engineering-dev.domino.tech/u/integration-test/autodoc-target-gbp/overview`
App URL: `https://biraadoc126819.engineering-dev.domino.tech/apps/ae9683eb-bbec-437b-b7b7-195df75daa4d?projectId=6a0caee08aa6aa0965406e83`
Project ID: `6a0caee08aa6aa0965406e83`

### Steps

1. Open the app URL above.
2. Click the Browse button.
3. The modal opens. The first option in the select should say `Source code` (no prefix, no path).
4. Remaining options should be dataset names (no `DS-` prefix).
5. With `Source code` selected, the file browser should list the repo root:
   - `noop/`, `spec2/`, `test-git1.yaml` (dirs + yaml only; `listener.py` filtered out)
   - No file sizes shown anywhere.
   - A "Loading..." message appears briefly while files fetch.
6. Navigate into a directory containing a `.yaml` file.
7. Click a `.yaml` file to select it (it highlights and the "Select" button activates).
8. Click Select.
9. The modal closes and the spec confirm bar shows the filename with "From code" label.
10. The template gallery refreshes and the imported spec appears.

### API sanity check

```
GET /apps/ae9683eb-bbec-437b-b7b7-195df75daa4d/api/code-root?projectId=6a0caee08aa6aa0965406e83
```

Expected response:
```json
{"isGit": true, "repoId": "6a0caee28aa6aa0965406e86", "location": "/mnt/code"}
```

If `repoId` is `6a0f007d7bb8e6117d64ef66` (AutoDocumentation_Extension), the fix did not deploy.

---

## DFS project test

Project: `https://biraadoc126819.engineering-dev.domino.tech/u/integration-test/autodoc-artifact-dfs1/overview`
Project ID: `6a16f390cf54ab6ccad5e4bf`
App URL: same deploy URL but with `?projectId=6a16f390cf54ab6ccad5e4bf`

### Steps

1. Open the app with the DFS project ID in the query string.
2. Click Browse.
3. First select option should say `Source code` (no prefix).
4. File browser shows the DFS code root (dirs + `.yaml`/`.yml` files only).
5. Navigate and select a `.yaml` file, confirm.
6. Spec confirm bar shows "From code".
7. Template gallery refreshes with the imported spec.

---

## Dataset source (regression)

1. In either project, open Browse.
2. Select a dataset option from the dropdown (shown by name, no `DS-` prefix).
3. File browser shows dataset contents (YAML only, no sizes).
4. Select a file, confirm.
5. Spec confirm bar shows "From dataset".
6. Template gallery refreshes.

---

## Deploy steps

```
git add -A
git commit -m "your message"
git push
```

Then stop and restart the app at:
`https://biraadoc126819.engineering-dev.domino.tech/u/integration-test/autodocs/apps/6a0cad5f8aa6aa0965406e75/latest/details/overview`

- Click the `...` menu (top right of the app details page)
- Click Stop, wait for status "Stopped"
- Click `...` again, click Start, wait for "Running"
