# Contributing to VGU Buddy

Start with the [README](README.md) and [repository audit](docs/repository-audit.md). The [implementation plan](implementation_plan_vgu_buddy.md) describes future work as well as completed frontend tasks; verify each task against current source before implementing it.

## Workflow

1. Describe the problem, expected behavior, and affected routes in an issue or pull request. Discuss broad architecture changes before expanding an existing feature.
2. Create a focused branch from the current default branch.
3. Install dependencies with `npm ci` in `apps/web` and run `npm run dev`.
4. Keep changes scoped. Update documentation when implementation status, configuration, or setup changes.
5. Run the relevant checks below and describe the results in the pull request.

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

In the pull request, describe the problem, resulting behavior, verification performed, and any remaining limitations. Include screenshots when a visible change benefits from review.

## Configuration and assets

Use `apps/web/.env.local` for local overrides. Keep credentials out of commits and out of `VITE_` configuration. Reuse existing brand assets; add genuine application screenshots only, without personal account data.

The repository currently has no project license file. A licensing decision is separate from this contribution guide.
