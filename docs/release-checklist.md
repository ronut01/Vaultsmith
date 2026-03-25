# Release Checklist

This checklist is for publishing Vaultsmith to PyPI with GitHub Actions Trusted Publishing.

## 1. Confirm the package name

As of 2026-03-25, `vaultsmith` returned `404` from the PyPI JSON API:

```text
https://pypi.org/pypi/vaultsmith/json
```

That indicates the project name is currently available.

## 2. Create the PyPI project with a trusted publisher

In PyPI, create the project and add a GitHub trusted publisher with these values:

- Owner: `ronut01`
- Repository name: `Vaultsmith`
- Workflow name: `publish.yml`
- Environment name: `pypi`

Use the workflow file:

- `.github/workflows/publish.yml`

The publish job already requests:

- `id-token: write`

## 3. Prepare the GitHub repository

In the GitHub repository:

1. Open `Settings -> Environments`
2. Create an environment named `pypi`
3. Leave protection rules minimal unless you want a manual approval gate

## 4. Verify the package locally

```bash
source .venv/bin/activate
pytest -q
python -m build
```

## 5. Tag and push a release

```bash
git tag v0.1.0
git push origin v0.1.0
```

Pushing a `v*` tag triggers the publish workflow.

## 6. Optional GitHub release

You can also create a GitHub release for the same tag, but the PyPI upload no longer depends on the release event because tag pushes are enough.
