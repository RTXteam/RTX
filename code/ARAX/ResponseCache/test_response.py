#!/usr/bin/python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import sys
import re
import json
import requests
import json

from reasoner_validator import validate_Response, ValidationError



############################################ Main ############################################################

#### If this class is run from the command line, perform a short little test to see if it is working correctly
def main():

    #### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='CLI testing of the ResponseCache class')
    argparser.add_argument('--verbose', action='count', help='If set, print more information about ongoing processing' )
    argparser.add_argument('response_id', type=str, nargs='*', help='Integer number of a response to read and display')
    params = argparser.parse_args()

    #### Query and print some rows from the reference tables
    if len(params.response_id) == 0 or len(params.response_id) > 1:
        eprint("Please specify a single ARS response UUID")
        return

    response_id = params.response_id[0]

    response_content = requests.get('https://ars.transltr.io/ars/api/messages/'+response_id, headers={'accept': 'application/json'})
    status_code = response_content.status_code

    if status_code != 200:
        eprint("Cannot fetch from ARS a response corresponding to response_id="+str(response_id))
        return

    #### Unpack the response content into a dict
    try:
        response_dict = response_content.json()
    except:
        eprint("Cannot decode ARS response_id="+str(response_id)+" to a Translator Response")
        return

    if 'fields' in response_dict and 'actor' in response_dict['fields'] and str(response_dict['fields']['actor']) == '9':
            eprint("The supplied response id is a collection id. Please supply the UUID for a response")
            return

    if 'fields' in response_dict and 'data' in response_dict['fields']:
        envelope = response_dict['fields']['data']
        if envelope is None:
            envelope = {}
            return envelope

        #### Perform a validation on it
        try:
            validate_Response(envelope)
            eprint('Returned message is valid')

        except ValidationError as error:
            eprint('ERROR: TRAPI validator reported an error: ' + str(error))
            if params.verbose:
                print(json.dumps(envelope, sort_keys=True, indent=2))

    return


if __name__ == "__main__": main()
