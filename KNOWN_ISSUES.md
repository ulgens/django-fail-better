# Known Issues

## `--maxfail` combined with `--pdb`

Django's `--pdb` and this runner's `--maxfail` serve conflicting purposes:

- `--maxfail` stops the run early, as soon as the failure limit is reached.
- `--pdb` drops into an interactive `pdb.post_mortem` session on the first failing test.

When both flags are enabled together, the runner composes `MaxFailResult` with
Django's `PDBDebugResult`. This is not recommended because:

- When the failure limit is hit, the runner opens a PDB session at the very failure
  that should have triggered a fast early exit, defeating the purpose of `--maxfail`.
- `PDBDebugResult` also overrides `addSubTest` (opening PDB on subtest errors), which
  the maxfail counting does not track, so failure counts can be inconsistent.

Prefer using `--maxfail` and `--pdb` as separate, mutually exclusive workflows.

## `--maxfail` does not count subtest failures

The maxfail failure counter tracks `addFailure`, `addError`, and
`addUnexpectedSuccess`, but not `addSubTest`. A failing subtest (via
`unittest.subTest`) therefore does not count toward the `--maxfail` budget.
