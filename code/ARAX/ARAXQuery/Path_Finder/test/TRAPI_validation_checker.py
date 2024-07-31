from reasoner_validator.validator import TRAPIResponseValidator
import json
from typing import Dict, List

trapi_version = '1.5.0'
biolink_version = '4.2.1'

validator = TRAPIResponseValidator(trapi_version=trapi_version, biolink_version=biolink_version)

with open('response.json', 'r') as file:
    json_string = file.read()
data = json.loads(json_string)
validator.check_compliance_of_trapi_response(data)
validation_messages_text = validator.dumps()
raw_messages: Dict[str, List[Dict[str, str]]] = validator.get_all_messages()
messages = raw_messages['Validate TRAPI Response']['Standards Test']
critical_errors = 0
errors = 0
if 'critical' in messages and len(messages['critical']) > 0:
    critical_errors = len(messages['critical'])
if 'error' in messages and len(messages['error']) > 0:
    errors = len(messages['error'])
print(f"# critical errors: {critical_errors}")
print(f"# errors: {errors}")
