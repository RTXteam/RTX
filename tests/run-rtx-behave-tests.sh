#!/bin/bash -e

echo -e "\n=================== STARTING SCRIPT ===================\n"

OUTPUT_REPORT="rtx-test-harness-report.json"
TESTING_REPO="translator-testing-framework"

echo -e "\nSETTING UP...\n"

# Create a local copy of the testing repo if we don't have one already
if [[ ! -d ${TESTING_REPO} ]]
then
    git clone --recursive https://github.com/RTXteam/translator-testing-framework.git
fi

# Start up a virtual environment
python3 -m venv behave-env
source behave-env/bin/activate

# Install requirements
cd ${TESTING_REPO}
git pull origin master
pip install -r requirements.txt

echo -e "\nRUNNING RTX BEHAVE TESTS...\n"
behave -i rtx-tests.feature -f json.pretty -o ../${OUTPUT_REPORT}

echo -e "\nUPLOADING REPORT TO S3...\n"
cd ..
aws s3 cp --no-progress --region us-west-2 ${OUTPUT_REPORT} s3://rtx-kg2-versioned/

echo -e "\nNOTIFYING STAFF IF FAILED TESTS...\n"
FAILED=$(grep -c failed ${OUTPUT_REPORT})
if [[ ${FAILED} ]]
then
    MESSAGE="There was an error: Tests failed in the RTX Behave harness."
    echo ${MESSAGE}
    # TODO: Add proper 'aws sns publish' line that sends message about failed tests
else
    echo "All tests passed - no need to notify anyone."
fi

echo -e "\n=================== SCRIPT FINISHED ===================\n"