<!-- GSD Configuration — managed by get-shit-done installer -->

# Instructions for GSD

- Use the get-shit-done skill when the user asks for GSD or uses a `gsd-*` command.
- Treat `/gsd-...` or `gsd-...` as command invocations and load the matching file from `.github/skills/gsd-*`.
- When a command says to spawn a subagent, prefer a matching custom agent from `.github/agents`.
- Do not apply GSD workflows unless the user explicitly asks for them.
- After completing any `gsd-*` command (or any deliverable it triggers: feature, bug fix, tests, docs, etc.), ALWAYS: (1) offer the user the next step by prompting via `ask_user`; repeat this feedback loop until the user explicitly indicates they are done.

# General Instructions

- **All questions to the user MUST use decision UI** (the `ask_user` / `vscode_askQuestions` tool with selectable options). NEVER end a message with a plain-text question and wait for the user to type a reply. Always present choices via the decision UI so the user can click to answer.
- This applies to every context: chat, CLI, GSD workflows, and subagents.
- **After completing ANY task** (GSD command, feature, bug fix, tests, docs, or any other deliverable), ALWAYS prompt the user via decision UI with at least these options: (1) "Kết thúc tại đây" (end), (2) suggested next actions relevant to the context. Always allow freeform text input so the user can type a custom request.
<!-- /GSD Configuration -->
