# Usage

1. Run all tests: `pytest -v`
1. Run all tests in a specific file: `pytest -v test_ARAX_overlay.py`
1. Run a certain test in a specific file: `pytest -v test_ARAX_overlay.py -k test_jaccard`

Note: Tests marked with `@pytest.mark.slow` are automatically skipped.
* To include slow tests, use `--runslow`
* To run only slow tests, use `--runonlyslow`

Example: `pytest -v --runslow`
