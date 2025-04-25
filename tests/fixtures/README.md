# LaTeX-to-LLM Tests

This directory contains the test suite for the LaTeX-to-LLM project.

## Test Structure

- `test_unit.py`: Unit tests for individual functions
- `test_integration.py`: Integration tests for the full workflow
- `test_cli.py`: Command-line interface tests
- `fixtures/`: Test LaTeX project fixtures used by the tests

## Running the Tests

To run all tests:

```bash
python -m unittest discover
```

To run a specific test file:

```bash
python -m unittest tests/test_unit.py
```

To run a specific test case:

```bash
python -m unittest tests.test_unit.TestLaTeXToLLM.test_collect_dependencies_simple
```

## Adding New Tests

When adding new tests:

1. Add unit tests to `test_unit.py` for any new functions
2. Add integration tests to `test_integration.py` for any new features
3. Add CLI tests to `test_cli.py` for any new command-line options
4. Add any necessary fixtures to the `fixtures/` directory

## Test Coverage

To generate a test coverage report (requires the `coverage` package):

```bash
coverage run -m unittest discover
coverage report
coverage html  # Generates an HTML report
```