# Contributing to Vaultsmith

Thanks for contributing.

Vaultsmith is still early, so the most helpful contributions are narrow, reviewable improvements that make the CLI, vault workflow, or docs easier to trust and adopt.

## Before you start

- Open an issue first for anything non-trivial.
- Keep changes small and reversible.
- Prefer real workflow improvements over speculative abstraction.
- If behavior changes, explain the user-facing impact clearly in the PR.

## Local setup

```bash
git clone https://github.com/ronut01/Vaultsmith.git
cd Vaultsmith
python -m venv .venv
source .venv/bin/activate
python -m pip install -e . pytest
```

## Run checks

```bash
pytest -q
ruff check .
```

## Contribution guidelines

- Prefer deletion over addition when possible.
- Preserve the review-first workflow.
- Keep docs aligned with actual shipped behavior.
- Do not add new dependencies without a strong reason.
- Include tests when changing CLI behavior or session flow.

## Pull requests

Please include:

- what changed
- why it changed
- how you tested it
- any follow-up work or known limitations

Good first contributions usually fit one of these buckets:

- docs clarity
- install and onboarding improvements
- safer session UX
- better tests
- smaller quality-of-life CLI fixes
