#!/usr/bin/python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import sys
import re
import json
import requests
import json
import copy
import timeit

#sys.path = ['/mnt/data/python/TestValidator'] + sys.path
from reasoner_validator.validator import TRAPIResponseValidator



############################################ Main ############################################################

def main():

    #### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='CLI testing of the ResponseCache class')
    argparser.add_argument('--verbose', action='count', help='If set, print more information about ongoing processing' )
    argparser.add_argument('response_id', type=str, nargs='*', help='UUID or integer number of a response to fetch and validate')
    params = argparser.parse_args()

    #### Query and print some rows from the reference tables
    if len(params.response_id) == 0 or len(params.response_id) > 1:
        eprint("Please specify a single ARS response UUID or ARAX response_id or local file name")
        return

    response_id = params.response_id[0]
    from_file = False

    if os.path.isfile(response_id):
        with open(response_id) as infile:
            response_dict = json.load(infile)
        status_code = 200
        from_file = True


        #### Muck with it
        #response_dict['message']['knowledge_graph']['edges'] = {}
        if False:
            target = response_dict['message']['knowledge_graph']['edges']
            keys = []
            ikey = 0
            for key,value in target.items():
                if ikey == 0:
                    ikey = ikey
                    #del(value['attributes'])
                    #del(value['sources'])
                if ikey > 0:
                    keys.append(key)
                ikey += 1
            for key in keys:
                del(target[key])
                print(f"Delete {key}")


    #### If a UUID / PK
    elif len(response_id) > 20:
        debug = True

        ars_hosts = [ 'ars-prod.transltr.io', 'ars.test.transltr.io', 'ars.ci.transltr.io', 'ars-dev.transltr.io', 'ars.transltr.io' ]
        for ars_host in ars_hosts:
            if debug:
                eprint(f"Trying {ars_host}...")
            try:
                response_content = requests.get(f"https://{ars_host}/ars/api/messages/"+response_id, headers={'accept': 'application/json'})
            except Exception as e:
                eprint( f"Connection attempts to {ars_host} triggered an exception: {e}" )
                return
            status_code = response_content.status_code
            if debug:
                eprint(f"--- Fetch of {response_id} from {ars_host} yielded {status_code}")
            if status_code == 200:
                break

        if status_code != 200:
            if debug:
                eprint("Cannot fetch from ARS a response corresponding to response_id="+str(response_id))
                eprint(str(response_content.content))
            return

    #### Otherwise assume an ARAX response id
    else:
        response_content = requests.get('https://arax.ncats.io/devED/api/arax/v1.4/response/'+response_id, headers={'accept': 'application/json'})
        status_code = response_content.status_code


    if status_code != 200:
        eprint("Cannot fetch a response corresponding to response_id="+str(response_id))
        return


    #### Unpack the response content into a dict
    if from_file is False:
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

    #### If there is a previous validation, remove it
    if 'validation_result' in envelope:
        del(envelope['validation_result'])

    #### Store the TRAPI before
    outfile = open('zz_before.json','w')
    print(json.dumps(envelope, sort_keys=True, indent=2), file=outfile)
    outfile.close()

    #### Perform a validation on it
    if params.verbose:
        print(json.dumps(envelope, sort_keys=True, indent=2))

    #validator = TRAPIResponseValidator(trapi_version="TranslatorReasonerAPI-1.4.0-beta4.yaml", biolink_version="3.2.8")
    t0 = timeit.default_timer()
    validator = TRAPIResponseValidator(trapi_version="1.5.0-beta", biolink_version="4.1.6")
    t1 = timeit.default_timer()
    validator.check_compliance_of_trapi_response(envelope)
    t2 = timeit.default_timer()

    messages: Dict[str, List[Dict[str,str]]] = validator.get_all_messages()
    print(json.dumps(messages, sort_keys=True, indent=2))

    print("-------------------------")
    validation_output = validator.dumps()
    print(validation_output)

    outfile = open('zz_after.json','w')
    print(json.dumps(envelope, sort_keys=True, indent=2), file=outfile)
    outfile.close()

    print("Object setup time: "+str(t1-t0))
    print("Validation time: "+str(t2-t1))


    return


if __name__ == "__main__": main()
