# Contributing to VGU Buddy

Start with the [README](README.md) and [repository audit](docs/repository-audit.md). The [implementation plan](implementation_plan_vgu_buddy.md) describes future work as well as completed frontend tasks; verify each task against current source before implementing it.

## Workflow

From FE-022 onward, tasks are implemented, committed and pushed directly on main unless repository protection prevents it.

1. Fetch origin, switch to `main`, inspect incoming changes and safely synchronize with `origin/main`. Start with a clean working tree.
2. Describe the problem, expected behavior and affected routes in the task report. Discuss broad architecture changes before expanding an existing feature.
3. Install dependencies with `npm ci` in `apps/web` when needed and run `npm run dev` for browser verification.
4. Keep changes scoped. Update documentation when implementation status, configuration or setup changes.
5. Run the relevant checks below and all required CI/security gates. Review the diff, check for unrelated files and scan for credentials before committing.
6. Commit directly on `main`. Fetch/check remote again before a normal push to `origin/main`; integrate and retest concurrent changes safely.
7. Verify the live remote SHA, CI result, clean working tree and ahead/behind state in the completion report.

Do not create a task branch, force push or rewrite history. If actual protection rules or a remote rejection require a pull request, report the evidence and preserve those rules; do not bypass them. Deployment requires a separate explicit request.

## Existing conventions

- Use TypeScript and preserve strict type checking.
- Reuse the local UI primitives and established VGU Buddy branding.
- Put public-facing copy in both `src/locales/en/common.json` and `src/locales/de/common.json`.
- Keep event UI separate from its repository, query, and validation layers. Sample posters belong to development fixtures.
- Keep form labels, keyboard navigation, focus handling, and reduced-motion behavior usable.
- Treat user/admin layout separation as scaffolding until authentication and authorization are implemented. Do not simulate a successful session to make a screen appear functional.

## Checks

From `apps/web`:

```sh
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

For UI behavior changes, update meaningful tests and check the affected routes in English and German. For documentation-only changes, check relative links, image rendering, commands, and feature claims; new application tests are not required.

In the completion report (or a pull request required by repository protection), describe the problem, resulting behavior, verification performed and any remaining limitations. Include screenshots when a visible change benefits from review.

## Configuration and assets

Use `apps/web/.env.local` for local overrides. Keep credentials out of commits and out of `VITE_` configuration. Reuse existing brand assets; add genuine application screenshots only, without personal account data.

The repository currently has no project license file. A licensing decision is separate from this contribution guide.
