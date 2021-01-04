#!/usr/bin/env bash
# This script runs all the RTX Behave tests and uploads JSON-formatted results to our S3 bucket; it notifies staff
# via SNS message if any tests failed. It requires aws-cli to be set up. Any relevant files (i.e., the testing repo
# and the output JSON report) are created in the directory the script is run from.

echo -e "\n=================== STARTING SCRIPT ===================\n"

REPORT_NAME="rtx-test-harness-report.json"
TESTING_REPO="translator-testing-framework"

echo -e "\nSETTING UP...\n"

# Create a local copy of the testing repo if we don't have one already
if [[ ! -d ${TESTING_REPO} ]]
then
    git clone --recursive https://github.com/RTXteam/translator-testing-framework.git
fi

# Start up a virtual environment for Behave and install requirements
python3 -m venv behave-env
source behave-env/bin/activate
cd ${TESTING_REPO}
git pull origin master
pip install -r requirements.txt

# Run all of our Behave tests, outputting a JSON report with results
echo -e "\nRUNNING RTX BEHAVE TESTS...\n"
behave -i rtx-tests.feature -f json.pretty -o ../${REPORT_NAME}
cd ..

# Notify staff via SNS if any tests failed
test_failed=$(grep -c failed ${REPORT_NAME})
if [[ ${test_failed} -gt 0 ]]
then
    echo -e "\nOne or more tests failed! Examine '${REPORT_NAME}' to see output."
    echo -e "\nNOTIFYING STAFF OF TEST FAILURE...\n"
    failure_message="Test(s) failed in the RTX Behave harness. See '${REPORT_NAME}' for results."
    aws sns publish --topic-arn arn:aws:sns:us-west-2:621419614036:rtx-testing --message ${failure_message}
else
    echo -e "\nAll tests passed!"
fi

# Upload the report to our S3 bucket
echo -e "\nUPLOADING REPORT TO S3 BUCKET...\n"
aws s3 cp --no-progress --region us-west-2 ${REPORT_NAME} s3://rtx-kg2-versioned/

echo -e "\n=================== SCRIPT FINISHED ===================\n"