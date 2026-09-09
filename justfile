# List available commands
default:
    @just --list --unsorted

# Run tests
[group("tests")]
test *ARGS:
    uv run pytest {{ ARGS }}
