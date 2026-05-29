# AutoDocumentation Extension - Use Cases

## UC-1: Generate model documentation from the Studio UI

As a Domino user working on a Domino project
I want to select a documentation template, configure the job, and click Generate
So that I get a complete, evidence-traced model documentation report (.docx) without writing code or managing LLM prompts manually.

**Acceptance Criteria:**
1. User can access the AutoDoc Extension from the Studio UI
2. Template gallery displays available templates with preview
3. User can select a template and configure basic options (output format, etc.)
4. Clicking Generate submits a job and shows progress/status
5. Job completes and produces a .docx file with model documentation
6. Document contains evidence citations linking back to source code

## UC-2: Customize the spec template before generating

As a Domino user
I want to edit the YAML spec directly in the UI - adding, removing, or rewording sections and hints - before submitting a job
So that the generated document reflects my model's specific context and my team's documentation standards.

**Acceptance Criteria:**
1. User can open an in-app editor for the selected template's YAML spec
2. Editor validates YAML syntax and highlights parse errors
3. User can add, remove, or modify documentation sections
4. Changes preview as parsed sections in real-time
5. User can save changes as a temporary override or submit generation immediately
6. Generated document reflects all customizations from the edited spec

## UC-3: Upload and share a custom spec template with the team

As a Domino user 
I want to upload a YAML spec file from my computer so it is saved in the project's autodoc dataset and appears in the shared gallery
So that my team can reuse a common documentation standard without each member maintaining their own copy.

**Acceptance Criteria:**
1. User can upload a YAML spec file via file browser in the UI
2. Uploaded file is validated for correct YAML syntax and required sections
3. File is stored in the project's autodoc dataset
4. Uploaded template appears in the template gallery for all users in the project
5. Uploaded template can be selected and used like built-in templates
6. File upload errors (invalid YAML, missing sections) are shown with guidance to fix

## UC-4: Configure generation with custom LLM and other settings

As a Domino user
I want to select a different LLM (e.g., Anthropic Claude, OpenAI GPT, open-source Llama) before submitting a job
So that I can use the model my team prefers or that best fits my documentation needs.

**Acceptance Criteria:**
1. UI displays available LLM options (built-in and configured integrations)
2. User can select an LLM before submitting a generation job
3. Selected LLM is used for the documentation generation run
4. Job output identifies which LLM was used in the metadata or header
5. LLM selection persists as default for future jobs (or user can change per-job)
6. If an LLM is unavailable or misconfigured, user sees a clear error message

## UC-5: Generate documentation for any project as an authenticated user

As a Domino user opening the AutoDoc app as an Extension from my own project
I want documentation jobs to run and store outputs under my project and identity
So that existing project permissions are honored without each team having to deploy their own copy of the app.

**Acceptance Criteria:**
1. AutoDoc Extension can be opened from any Domino project's Studio UI
2. Jobs run under the visiting user's identity (not app owner)
3. Output files are saved to the visiting user's project workspace
4. Job history reflects the correct project context
5. Users can only access their own project's job history and outputs
6. App correctly handles permissions; users cannot access or run jobs on projects they don't have access to
