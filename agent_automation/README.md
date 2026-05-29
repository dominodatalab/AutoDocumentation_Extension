# agent_automation

Reproducible setup and procedures for the Claude Code agent working on
`AutoDocumentation_Extension`. The agent uses the `chrome-devtools` MCP server
to drive a real Chrome session against the Domino app environment.

Files:

- `task_brief.md` - the source-of-truth task brief: original directions,
  clarifying questions, and answers that scope what the agent is and is
  not allowed to do on this work.
- `setup.md` - one-time host setup (Node 20 via asdf, MCP wrapper, MCP
  registration, Chrome launch flags).
- `deploy.md` - how the agent redeploys the target Domino app after
  pushing code (stop / wait / start / wait flow with the verified
  `data-test` selectors and the `/latest/` URL form).
- `scripts/launch_chrome.sh` - launches Chrome with remote debugging on
  port 9222 against an isolated profile.
- `scripts/redeploy_app.py` - Python helper that performs the stop / start
  cycle against the Domino app via the Chrome DevTools Protocol. Intended
  for manual operator use; the agent itself drives Chrome through MCP
  tools.
- `screenshots/` - reference screenshots captured during agent runs.

## External references

- Domino backend source (the platform serving the jobs API, app
  publisher, env vars like `DOMINO_RUN_ID`, etc.) is checked out at
  `/Users/biraignacio/Documents/dev/src/domino`. Grep there when you
  need to understand server-side behavior (e.g. which env vars get
  injected into a job pod, how the logs endpoint streams, what the
  `/v4/jobs/<id>/...` responses look like).
