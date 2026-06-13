# Contributing to SymPress

Thanks for considering a contribution to SymPress.

SymPress implements Symfony components and architecture patterns in WordPress. Contributions should respect both sides: WordPress remains the runtime and integration surface, while Symfony components provide structure where that structure makes projects easier to build, test, and maintain.

## Ways to Contribute

- Report reproducible bugs.
- Suggest focused features with a clear WordPress use case.
- Improve documentation and examples.
- Add tests for existing behavior.
- Refine package APIs, contracts, and configuration.

## Before You Start

- Search existing issues and pull requests.
- Open an issue for larger changes before investing significant time.
- Keep proposals scoped to one problem.
- Prefer incremental adoption over framework-wide assumptions.

## Development Principles

- WordPress behavior should remain visible and understandable.
- Symfony components should be used through clear package boundaries.
- Public APIs should be stable, typed where possible, and documented.
- Configuration should be explicit and predictable.
- Tests should cover package behavior and WordPress integration boundaries.

## Pull Requests

1. Fork or branch from the current default branch.
2. Make the smallest change that solves the problem.
3. Add or update tests when behavior changes.
4. Update documentation for user-facing APIs or configuration.
5. Fill out the pull request template with verification notes.

## Commit Style

Use Conventional Commits with a focused scope when useful:

```text
feat(setup): generate local admin passwords
fix(ci): call reusable SymPress QA
docs: document ddev.site defaults
```

## Review

Maintainers may ask for changes to scope, naming, documentation, or tests. Review is part of keeping SymPress packages consistent across WordPress and Symfony expectations.

## License

By contributing, you agree that your contribution is licensed under the project license.
