# Publishing to PyPI

Package name: **agentic-loop**

## One-time setup

1. Create accounts: [PyPI](https://pypi.org/account/register/) and [TestPyPI](https://test.pypi.org/account/register/)
2. Enable [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) on PyPI for this GitHub repo (recommended)
   - Or create an API token for manual upload

## Build locally

```powershell
pip install build twine
python -m build
twine check dist/*
```

## Upload to TestPyPI

```powershell
twine upload --repository testpypi dist/*
pip install -i https://test.pypi.org/simple/ agentic-loop
```

## Upload to PyPI

```powershell
twine upload dist/*
```

After release, users install with:

```powershell
pip install agentic-loop

# extras
pip install "agentic-loop[webhook]"
pip install "agentic-loop[mcp]"
pip install "agentic-loop[all]"
```

## GitHub Release workflow

Tag a release to trigger [.github/workflows/publish-pypi.yml](../.github/workflows/publish-pypi.yml):

```powershell
git tag v0.3.0
git push origin v0.3.0
```

Create a GitHub Release for the tag (workflow runs on `release: published`).

## Version bump checklist

1. Update `version` in `pyproject.toml` and `agentic_loop/__init__.py`
2. Update `CHANGELOG` section in README if needed
3. Tag `vX.Y.Z` and publish release
