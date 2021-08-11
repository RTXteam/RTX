# Usage

1. Run all tests: `pytest -v`
1. Run all tests in a specific file: `pytest -v test_ARAX_overlay.py`
1. Run a certain test in a specific file: `pytest -v test_ARAX_overlay.py -k test_jaccard`

Note: Tests marked with `@pytest.mark.slow` or `@pytest.mark.external` are automatically skipped. The 'external' tag is meant for tests that rely on an external KP (e.g., used through an API). 

A test can be marked with more than one tag (e.g., slow *and* external).


* To include slow tests, use `--runslow`
* To include external tests, use `--runexternal`
* To run _only_ slow tests, use `--runonlyslow`
* To run _only_ external tests, use `--runonlyexternal`

Example: Running `pytest -v --runslow --runexternal` will include all tests.

#### Helpful tips:
You can list the top, say, 10 slowest tests by adding the flag `--durations=10`.

Use the `-s` option to display output (it's suppressed by default, unless a test fails).

Tests are selected based on name matches, so `pytest -v test_ARAX_resultify.py -k test_issue720` will run:
```
test_ARAX_resultify.py::test_issue720_1 PASSED                            [ 33%]
test_ARAX_resultify.py::test_issue720_2 PASSED                            [ 66%]
test_ARAX_resultify.py::test_issue720_3 PASSED                            [100%]
```
