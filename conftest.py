# Intentionally empty.
#
# Its presence at the project root (not just inside tests/) makes pytest
# treat this directory as the rootdir for sys.path insertion, so `import app`
# works whether pytest is invoked as `pytest`, `python -m pytest`, or from
# a different working directory. Without this file, `tests/conftest.py`
# alone causes pytest to add only `tests/` to sys.path (since it has no
# `__init__.py`), not the project root where the `app` package actually
# lives — which is exactly the ModuleNotFoundError this fixes.
