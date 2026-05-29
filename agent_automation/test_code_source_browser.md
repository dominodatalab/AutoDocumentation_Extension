# Test plan: code source browser feature

## What was implemented

The "Browse spec files" modal now shows both datasets and the project's git/code repo as sources.

- Select shows code source first (prefixed `Git-` or `Code-`) then datasets prefixed `DS-`
- File browser fetches from `/api/code-files` for code, `/api/dataset-files` for datasets
- For code sources, only `.yaml`/`.yml` files are shown (dirs always shown)
- Selecting a file and confirming copies it to the autodoc dataset (same as before)
- File size display removed everywhere
- Label changed from "Dataset" to "Source"

## GBP project test

Project: `https://biraadoc126819.engineering-dev.domino.tech/u/integration-test/autodoc-gbp1/overview`
App URL: `https://biraadoc126819.engineering-dev.domino.tech/apps/ae9683eb-bbec-437b-b7b7-195df75daa4d?projectId=6a0caee08aa6aa0965406e83`
Project ID: `6a0caee08aa6aa0965406e83`

### Steps

1. Open the app URL above.
2. Click the Browse button (magnifying glass icon near the spec template field).
3. The modal opens. The first option in the select should be prefixed `Git-` and show `/mnt/code` or the repo's location.
4. Remaining options should be prefixed `DS-` for datasets.
5. With the `Git-` option selected, the file browser should list the repo root contents.
   - Only directories and `.yaml`/`.yml` files are shown.
   - No file sizes are shown anywhere.
6. Navigate into a directory containing a `.yaml` file.
7. Click a `.yaml` file to select it (it highlights and the "Confirm" button activates).
8. Click Confirm.
9. The modal closes and the spec confirm bar shows the filename with "From code" label (not "From dataset").
10. The template gallery refreshes and the imported spec appears.

### Verifying the copy worked

Check the autodoc dataset for the project. The file should appear under `spec-templates/<filename>`.

## DFS project test

Project: `https://biraadoc126819.engineering-dev.domino.tech/u/integration-test/autodoc-artifact-dfs1/overview`
Project ID: `6a16f390cf54ab6ccad5e4bf`
App URL: same deploy URL but with `?projectId=6a16f390cf54ab6ccad5e4bf`

### Steps

1. Open the app with the DFS project ID in the query string.
2. Click Browse.
3. The first select option should be prefixed `Code-` (not `Git-`) showing `/mnt` or similar.
4. File browser shows the DFS code root (dirs + `.yaml`/`.yml` files only).
5. Navigate and select a `.yaml` file, confirm.
6. Spec confirm bar shows "From code".
7. Template gallery refreshes with the imported spec.

## Dataset source (regression)

1. In either project, open Browse.
2. Select a `DS-` prefixed option from the dropdown.
3. File browser shows dataset contents (YAML only, no sizes).
4. Select a file, confirm.
5. Spec confirm bar shows "From dataset".
6. Template gallery refreshes.

## Deploy steps

```
# in repo root
git add -A
git commit -m "feat: extend browse modal to support git/DFS code sources"
git push
```

Then stop and restart the app at:
`https://biraadoc126819.engineering-dev.domino.tech/u/integration-test/autodocs/apps/6a0cad5f8aa6aa0965406e75/latest/details/overview`

- Click `data-test="apps-details-page-actions-more-actions-menu-trigger"`
- Click `data-test="app-run-control-stop"`, wait for status "Stopped"
- Click menu trigger again, click `data-test="app-run-control-start"`, wait for "Running"
