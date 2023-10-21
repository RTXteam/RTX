#!/usr/bin/python3

import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)
import os
import re
import json
from datetime import datetime
import json
import requests
import requests_cache
import copy

from node_synonymizer import NodeSynonymizer


class RecentUUIDManager:

    def __init__(self):
        self.synonymizer = None


    def get_recent_uuids(self, ars_host='ars.ci.transltr.io', top_n_pks=20):

        debug = False
        #top_n_pks = 20
        response = { 'agents_list': [], 'pks': {} }

        #ars_hosts = [ 'ars-prod.transltr.io', 'ars.test.transltr.io', 'ars.ci.transltr.io', 'ars-dev.transltr.io', 'ars.transltr.io' ]
        #ars_hosts = [ 'ars.test.transltr.io' ]
        ars_hosts = [ ars_host ]
        for ars_host in ars_hosts:
            with requests_cache.disabled():
                if debug:
                    eprint(f"Trying {ars_host}...")
                try:
                    response_content = requests.get(f"https://{ars_host}/ars/api/latest_pk/{top_n_pks}", headers={'accept': 'application/json'})
                except Exception as e:
                    return( { "status": 404, "title": f"Remote host {ars_host} unavailable", "detail": f"Connection attempts to {ars_host} triggered an exception: {e}", "type": "about:blank" }, 404)
            status_code = response_content.status_code
            if debug:
                eprint(f"--- Fetch of UUIDs from {ars_host} yielded {status_code}")
            if status_code == 200:
                if debug:
                    eprint(f"Got 200 from {ars_host}...")
                break

        if status_code != 200:
            error_message = f"Cannot fetch recent pks from any ARS hosts"
            if debug:
                eprint(error_message)
                eprint(str(response_content.content))
            return( { "status": 404, "title": "Response not found", "detail": error_message, "type": "about:blank" }, 404)


        #### Unpack the response content into a dict
        try:
            response_dict = response_content.json()
        except:
            return( { "status": 404, "title": "Error decoding Response", "detail": f"Cannot decode recent PK list from ARS {ars_host}", "type": "about:blank" }, 404)

        #### Debugging
        if debug:
            temp = copy.deepcopy(response_dict)
            #temp['fields']['data'] = '...'
            eprint(json.dumps(temp,indent=2,sort_keys=True))

        container_key = f"latest_{top_n_pks}_pks"
        if container_key not in response_dict:
            return( { "status": 404, "title": "Error decoding Response", "detail": f"Cannot decode recent PK list from ARS {ars_host}: cannot find {container_key}", "type": "about:blank" }, 404)

        for uuid in response_dict[container_key]:
            #eprint(f"UUID is {uuid}")
            uuid_data = self.get_uuid(ars_host, uuid)
            #eprint(json.dumps(uuid_data,indent=2,sort_keys=True))
            result = self.summarize_uuid_data(ars_host, uuid_data)
            response['pks'][uuid] = result
            response['agents_list'] = result['agents_list']
            del(result['agents_list'])
            response['pks'][uuid]['ars_host'] = ars_host
            #eprint(json.dumps(response,indent=2,sort_keys=True))

        return response


    ###################################################################
    def get_uuid(self, ars_host, uuid):

        debug = False

        if debug:
            eprint(f"Trying to fetch {uuid} from {ars_host}...")
        try:
            response_content = requests.get(f"https://{ars_host}/ars/api/messages/{uuid}", headers={'accept': 'application/json'})
        except Exception as e:
            return( { "status": 404, "title": f"Remote host {ars_host} unavailable", "detail": f"Connection attempts to {ars_host} triggered an exception: {e}", "type": "about:blank" }, 404)

        status_code = response_content.status_code
        if debug:
            eprint(f"--- Fetch of {uuid} from {ars_host} yielded {status_code}")

        if status_code != 200:
            if debug:
                eprint("Cannot fetch from ARS the UUID {uuid}")
                eprint(str(response_content.content))
            return( { "status": 404, "title": "Response not found", "detail": f"Cannot fetch from ARS a UUID {uuid}", "type": "about:blank" }, 404)


        #### Unpack the response content into a dict
        try:
            response_dict = response_content.json()
        except:
            return( { "status": 404, "title": "Error decoding Response", "detail": f"Cannot decode UUID {uuid} data from {ars_host}", "type": "about:blank" }, 404)


        is_parent_pk = False
        if 'fields' in response_dict:
            if 'name' in response_dict['fields'] and response_dict['fields']['name'] != '':
                if response_dict['fields']['name'] == 'ars-default-agent' or response_dict['fields']['name'] == 'ars-workflow-agent':
                    is_parent_pk = True
                else:
                    is_parent_pk = False
            elif 'actor' in response_dict['fields'] and ( str(response_dict['fields']['actor']) == '9' or str(response_dict['fields']['actor']) == '19' ):
                is_parent_pk = True

        if is_parent_pk == True:
            with requests_cache.disabled():
                if debug:
                    eprint(f"INFO: This is a parent UUID. Fetching trace=y for {uuid}")
                response_content = requests.get(f"https://{ars_host}/ars/api/messages/{uuid}?trace=y", headers={'accept': 'application/json'})
            status_code = response_content.status_code

            if status_code != 200:
                return( { "status": 404, "title": "Response not found", "detail": "Failed attempting to fetch trace=y from ARS with UUID {uuid}", "type": "about:blank" }, 404)

            #### Unpack the response content into a dict and dump
            try:
                response_dict = response_content.json()
            except:
                return( { "status": 404, "title": "Error decoding Response", "detail": f"Cannot decode UUID {uuid} data from {ars_host}", "type": "about:blank" }, 404)

            return response_dict

        if not is_parent_pk and 'fields' in response_dict and 'data' in response_dict['fields']:
            envelope = response_dict['fields']['data']
            if debug:
                eprint(f"INFO: This is an ordinary child UUID. Don't know what to do with it...")
            return( { "status": 404, "title": "No Parent PK", "detail": "This is an ordinary child UUID. Don't know what to do with it.", "type": "about:blank" }, 404)


        return response_dict


    ###################################################################
    def summarize_uuid_data(self, ars_host, uuid_data):

        summary = { 'agents': {} }
        agents = {}

        if 'status' in uuid_data:
            summary['status'] = uuid_data['status']

        if 'timestamp' in uuid_data:
            summary['timestamp'] = uuid_data['timestamp']

        if 'children' in uuid_data:
            for actor_response in uuid_data['children']:
                code = '-'
                status = '-'
                result_count = 0
                agent = '?'
                if 'actor' in actor_response:
                    if 'agent' in actor_response['actor']:
                        agent = actor_response['actor']['agent']
                if not agent.startswith('ara'):
                    continue
                agent = agent.replace('ara-', '')
                agents[agent] = True
                if 'code' in actor_response:
                    code = actor_response['code']
                if 'status' in actor_response:
                    status = actor_response['status']
                if 'result_count' in actor_response:
                    result_count = actor_response['result_count']
                    if result_count is None:
                        result_count = 0
                code_str = ''
                if code != 200:
                    code_str = f"={code}"
                #summary[agent] = f"{status}{code_str} ({result_count} results)"
                summary['agents'][agent] = { 'status': f"{status}{code_str}", 'n_results': result_count }

        if 'query_graph' in uuid_data:
            predicate ='?'
            object_id ='?'
            if 'edges' in uuid_data['query_graph']:
                n_edges = len(uuid_data['query_graph']['edges'])
                for edge_name,edge in uuid_data['query_graph']['edges'].items():
                    if 'predicates' in edge and edge['predicates'] is not None and len(edge['predicates']) > 0:
                        predicate = edge['predicates'][0]
            if 'nodes' in uuid_data['query_graph']:
                n_nodes = len(uuid_data['query_graph']['nodes'])
                for node_name,node in uuid_data['query_graph']['nodes'].items():
                    if 'ids' in node and node['ids'] is not None and len(node['ids']) > 0:
                        object_id = node['ids'][0]
            predicate = predicate.replace('biolink:', '')

            if self.synonymizer is None:
                self.synonymizer = NodeSynonymizer()
            results = self.synonymizer.get_normalizer_results(entities=object_id)
            try:
                name = results[object_id]['id']['name']
                #eprint(json.dumps(results[object_id]['id'], indent=2))
                if name is not None and len(name) > 1:
                    object_id = name
            except:
                eprint(f"ERROR: Unable to name name for {object_id} from synonymizer")

            summary['query'] = f"___ {predicate} {object_id}"

        summary['agents_list'] = sorted(list(agents.keys()))

        return summary


############################################ Main ############################################################

#### If this class is run from the command line, perform a short little test to see if it is working correctly
def main():

    #### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='CLI testing of the ResponseCache class')
    argparser.add_argument('--verbose', action='count', help='If set, print more information about ongoing processing' )
    argparser.add_argument('response_id', type=str, nargs='*', help='Id of a response to fetch and display')
    params = argparser.parse_args()

    manager = RecentUUIDManager()

    manager.get_recent_uuids()


if __name__ == "__main__": main()
