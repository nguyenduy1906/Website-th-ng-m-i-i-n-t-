# AGENTS.md

## Package manager

- Use `npm` for this workspace. Confirm this before installing dependencies.
- Run package scripts with `npm run <script>`.

## Related instruction files

- Before implementing or changing the website, read `docs/nghiep-vu-goc.txt` for the business requirements and `docs/README.md` for the agreed implementation scope. Apply both to UI, backend, data models, and business flows. Only admin and customer/public interfaces are in scope; do not infer separate employee interfaces from the broader source document.
- Also check `DESIGN.md` when the task touches matching tooling or design behavior.
- For NEU SHOP UI tasks, use `.agents/skills/neu-shop-design/SKILL.md` and treat `DESIGN.md` as the single source of truth for colors, typography, layout, components, and responsive behavior.
- UI UX Pro Max is installed at `.agents/skills/ui-ux-pro-max`; use its `SKILL.md` for NEU SHOP design/redesign work. The unmodified source is in `tools/ui-ux-pro-max`. Apply its search guidance to the existing FastAPI/Jinja2 stack; `DESIGN.md` remains the final project specification and no framework/package installation is implied.
- Hallmark is installed at `.agents/skills/hallmark`; use it for new UI design and when the user explicitly requests Hallmark redesign/audit. Read its `SKILL.md` before use. Existing UI edits otherwise follow the project's own system. `DESIGN.md` and these workspace instructions take precedence over conflicting Hallmark defaults, including CSS header comments. Keep upstream files unchanged; record project adaptations in `DESIGN.md`.

## Comment style

- Never place comments on the first two lines of a source file; start with imports or declarations.
- Prefer concise section headings such as `// ── Constants ──` or a three-line banner for major sections so files remain easy to scan.
- Use JSDoc blocks only when an API, intent, edge case, or constraint needs explanation; do not restate the code.

## Boundaries

- Prefer existing local patterns and helper APIs before adding new abstractions.
- Keep generated, packaged, and runtime asset boundaries intact; do not move files across host/webview ownership without updating build and packaging config.
