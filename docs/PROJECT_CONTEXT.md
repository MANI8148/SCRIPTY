# SCRIPTY Project Context

SCRIPTY is a Python 3.14 historical story generation system. It currently has:

- Multi-mode generation: short, chapter, book.
- Async location enrichment with cache fallback.
- Lazy dataset loading and entity validation.
- Background job queue for book generation.
- Flask REST API and vanilla frontend.
- Basic performance, narrative, and system metrics.

## Current Stable Commands

```bash
.venv/bin/python -m pytest -q
PORT=5001 .venv/bin/python -m backend.app
```

## Contributor Checklist

Before starting work:

1. Check `git status --short`.
2. Review the relevant modules and tests before making changes.
3. Avoid committing generated files or local environment artifacts.

Before finishing work:

1. Run focused tests for changed code.
2. Run full tests when feasible.
3. Update documentation when behavior or configuration changes.
4. Mention any known incomplete items.
