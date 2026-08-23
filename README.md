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

---

## Rationale

Teams that want `--last-failed`, `--maxfail`, or `--failed-first` currently must either migrate to `pytest-django` or implement these themselves. This runner fills that gap: set `TEST_RUNNER` once and get the workflow you'd expect from pytest, without leaving `manage.py test`.

No existing PyPI package provides these features as a `DiscoverRunner` subclass.

---

## Installation

```bash
pip install django_fail_better
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add django_fail_better
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

### CLI Options

| Flag                        | Short       | Description                                                    |
|-----------------------------|-------------|----------------------------------------------------------------|
| `--last-failed`             | `--lf`      | Only run tests that failed the last time                       |
| `--failed-first`            | `--ff`      | Run failed tests first, then the rest                          |
| `--last-failed-no-failures` | `--lfnf`    | What to do when `--last-failed` has no cache (`all` or `none`) |
| `--maxfail`                 |             | Stop after N failures (0 means never stop)                     |
| `--cache-show`              |             | Show the contents of the last-failed cache                     |
| `--cache-clear`             |             | Clear the last-failed cache before running                     |
| `--stepwise`                | `--sw`      | Stop at first failure and resume from it on the next run       |
| `--stepwise-skip`           | `--skip-sw` | Ignore the stepwise cache and run all tests                    |

---

_Test again, fail better!_
