#!/usr/bin/python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import sys
import re
import json
import requests
import json

sys.path = ['/mnt/data/python/TestValidator'] + sys.path
from reasoner_validator import TRAPIResponseValidator



############################################ Main ############################################################

#### If this class is run from the command line, perform a short little test to see if it is working correctly
def main():

    #### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='CLI testing of the ResponseCache class')
    argparser.add_argument('--verbose', action='count', help='If set, print more information about ongoing processing' )
    argparser.add_argument('response_id', type=str, nargs='*', help='UUID or integer number of a response to fetch and validate')
    params = argparser.parse_args()

    #### Query and print some rows from the reference tables
    if len(params.response_id) == 0 or len(params.response_id) > 1:
        eprint("Please specify a single ARS response UUID")
        return

    response_id = params.response_id[0]

    if len(response_id) > 20:
        response_content = requests.get('https://ars-dev.transltr.io/ars/api/messages/'+response_id, headers={'accept': 'application/json'})
    else:
        response_content = requests.get('https://arax.ncats.io/devED/api/arax/v1.3/response/'+response_id, headers={'accept': 'application/json'})

    status_code = response_content.status_code

    if status_code != 200:
        eprint("Cannot fetch a response corresponding to response_id="+str(response_id))
        return

    #### Unpack the response content into a dict
    try:
        response_dict = response_content.json()
    except:
        eprint("Cannot decode Response with response_id="+str(response_id)+" into JSON")
        return

    if 'fields' in response_dict and 'actor' in response_dict['fields'] and str(response_dict['fields']['actor']) == '9':
            eprint("The supplied response id is a collection id. Please supply the UUID for a single Response")
            return

    if 'fields' in response_dict and 'data' in response_dict['fields']:
        envelope = response_dict['fields']['data']
        if envelope is None:
            envelope = {}
            return envelope
    else:
        envelope = response_dict

    #### Perform a validation on it
    if params.verbose:
        print(json.dumps(envelope, sort_keys=True, indent=2))
    validator = TRAPIResponseValidator(trapi_version="1.4.0-beta", biolink_version="3.2.1")
    validator.check_compliance_of_trapi_response(envelope)
    messages: Dict[str, List[Dict[str,str]]] = validator.get_messages()

    print(json.dumps(messages, sort_keys=True, indent=2))

    return


if __name__ == "__main__": main()
