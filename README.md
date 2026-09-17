<div align="center">

# django-fail-better

[![Python](https://img.shields.io/badge/python->=3.12,<3.16-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django->=5.2,<6.2-092E20?&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![uv](https://img.shields.io/badge/-uv-DE5FE9?logo=uv&labelColor=555)](https://github.com/astral-sh/uv)
[![prek](https://img.shields.io/badge/-prek-F54327?logo=prek&labelColor=555)](https://github.com/j178/prek)
[![Ruff](https://img.shields.io/badge/-ruff-D7FF64?logo=ruff&labelColor=555)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/badge/-ty-46EBE1?logo=ty&labelColor=555)](https://github.com/astral-sh/ty)
[![Renovate](https://img.shields.io/badge/-renovate-308BE3?logo=renovate&labelColor=555)](https://github.com/renovatebot/renovate)

[![Git Hooks](https://img.shields.io/github/actions/workflow/status/ulgens/django-fail-better/git-hooks.yml?logo=github&label=Git%20Hooks)](https://github.com/ulgens/django-fail-better/actions/workflows/git-hooks.yml)
[![Tests](https://img.shields.io/github/actions/workflow/status/ulgens/django-fail-better/tests.yml?logo=github&label=Tests)](https://github.com/ulgens/django-fail-better/actions/workflows/tests.yml)

</div>

A drop-in TEST_RUNNER for Django's manage.py test that brings pytest-style workflow features to the native Django test runner. No pytest migration required.

## Installation

```bash
pip install django_fail_better
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install django_fail_better
```

## Usage

```python
# settings.py
TEST_RUNNER = "django_fail_better.FailBetterRunner"
```

```bash
# CLI
python manage.py test --lf --maxfail=3
```

## Options

All options are passed to `manage.py test` like any other test runner argument.

| Option                      | Alias        | Type / Choices | Default         | Description                                                                                                                                                                                                                                                                           |
|-----------------------------|--------------|----------------|-----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--last-failed`             | `--lf`       | flag           | `False`         | Run only the tests that failed at the last run (or all if none failed).                                                                                                                                                                                                               |
| `--last-failed-no-failures` | `--lfnf`     | `all` / `none` | `all`           | With ``--lf``, determines whether to execute tests when there are no previously (known) failures or when no cached ``lastfailed`` data was found. ``all`` (the default) runs the full test suite again. ``none`` just emits a message about no known failures and exits successfully. |
| `--failed-first`            | `--ff`       | flag           | `False`         | Run all tests, but run the last failures first.                                                                                                                                                                                                                                       |
| `--maxfail`                 | —            | `int`          | `0` (unlimited) | Exit after first num failures or errors                                                                                                                                                                                                                                               |
| `--failure-cache-show`      | —            | flag           | `False`         | Show failure cache contents, don't perform collection or tests.                                                                                                                                                                                                                       |
| `--failure-cache-clear`     | —            | flag           | `False`         | Remove all failure cache contents at start of test run.                                                                                                                                                                                                                               |
| `--stepwise`                | `--sw`       | flag           | `False`         | Exit on test failure and continue from last failing test next time                                                                                                                                                                                                                    |
| `--stepwise-skip`           | `--sw-skip`  | flag           | `False`         | Ignore the first failing test but stop on the next failing test. Implicitly enables --stepwise.                                                                                                                                                                                       |
| `--stepwise-reset`          | `--sw-reset` | flag           | `False`         | Resets stepwise state, restarting the stepwise workflow. Implicitly enables --stepwise.                                                                                                                                                                                               |
