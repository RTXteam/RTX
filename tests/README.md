# Behave testing harness for RTX

As part of the larger [translator-testing-framework](https://github.com/NCATS-Tangerine/translator-testing-framework), 
we've created a testing harness for RTX using [Behave](https://behave.readthedocs.io/en/latest/), a Python-based 
behavior-driven development testing framework. These tests ask RTX questions through the [RTX OpenAPI](https://rtx.ncats.io/api/rtx/v1/ui/)
(which currently uses KG1), and compare its answers to ground truths.

### To get set up

First, create and start up a Python **virtual environment**:

    python3 -m venv behave-env

    source behave-env/bin/activate

Then **clone the [RTX fork](https://github.com/RTXteam/translator-testing-framework)** of translator-testing-framework:

    git clone --recursive https://github.com/RTXteam/translator-testing-framework.git
    
Then navigate into your newly created directory and **sync the fork** to the original repository:

    cd translator-testing-framework
    
    git remote add upstream https://github.com/NCATS-Tangerine/translator-testing-framework.git

    git pull upstream master
    
And run this to **install packages**:

    pip install -r requirements.txt

### To run the tests

Use this command to run **all of the RTX tests**:

    behave -i rtx-tests.feature

Use `behave -n "[scenario name]"` to run **only a particular test**, e.g.:

    behave -n "Fanconi anemia is associated with expected genes"

NOTE: In addition to RTX, `translator-testing-framework` contains tests for various other Translator projects; you can run
_all_ of the tests (across all projects) using the command `behave`, but beware that other projects' tests may have further
dependencies not detailed here, and thus may not run properly.

### Contributing code

The going protocol for contributing is to push changes to our RTX fork, and then make pull requests from our fork 
to the [original repository](https://github.com/NCATS-Tangerine/translator-testing-framework).

Currently, all of the RTX-specific tests live in one feature file: [rtx-tests.feature](https://github.com/RTXteam/translator-testing-framework/blob/master/features/rtx-tests.feature). 
The Python implementations of the steps these tests use are currently in the main [steps.py](https://github.com/RTXteam/translator-testing-framework/blob/master/features/steps/steps.py) 
file (along with various other projects' step implementations).