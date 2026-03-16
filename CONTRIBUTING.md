# Contributing

This is a solo-maintained project released with the goal of being useful. Contributions are welcome, but please set expectations accordingly.

## Response Time

Issues and PRs are reviewed in batches, typically weekly. If something is urgent, open an issue and describe why.

## How to Contribute

### Submit an Example

The most valuable contribution is a new pattern builder:

1. Create a new builder script in `patterns/` following the existing pattern
2. Generate the `.excalidraw` output in `examples/`
3. Render to PNG using `engine/render_excalidraw.py`
4. Submit a PR with the builder + excalidraw + PNG

Good example submissions:
- Solve a layout problem the existing 4 patterns don't cover
- Use the engine's features (arrow routing, profiles, typography)
- Include generic content (no client-specific data)

### Report a Bug

Open an issue with:
- What you expected
- What happened instead
- The `.excalidraw` file or builder script that reproduces it
- A screenshot if it's a visual issue

### Suggest a Feature

Open an issue. Describe the use case before the solution.

## Code Style

- Python: formatted with Ruff, 88-character line limit
- Type hints for all function signatures
- Docstrings for public functions

## What I Won't Merge

- Changes that break existing pattern builders
- Dependencies beyond Playwright (the engine should stay lightweight)
- Client-specific content or branding in examples

## License

By contributing, you agree that your contributions will be licensed under MIT.
