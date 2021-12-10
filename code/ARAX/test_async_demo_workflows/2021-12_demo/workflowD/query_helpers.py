from collections import defaultdict
import json
from typing import Any, Dict, Iterable, List, Set, Tuple, Union
from urllib.parse import urlencode  

import requests

ARAX_QUERY_ARG_ID = 'id'
ARAX_QUERY_ARG_SOURCE = 'source'
ARAX_SOURCE_ARS = 'ARS'
ARAX_URL = 'https://arax.ncats.io/'

ARS_QUERY_ARG_TRACE = 'trace'
ARS_RESP_KEY_ACTOR = 'actor'
ARS_RESP_KEY_AGENT = 'agent'
ARS_RESP_KEY_CHILDREN = 'children'
ARS_RESP_KEY_DATA = 'data'
ARS_RESP_KEY_FIELDS = 'fields'
ARS_RESP_KEY_MESSAGE = 'message'
ARS_RESP_KEY_RESULTS = 'results'
ARS_RESP_KEY_STATUS = 'status'
ARS_STATUS_DONE = 'Done'
ARS_STATUS_ERROR = 'Error'
ARS_TRACE_PARAMS = {ARS_QUERY_ARG_TRACE: 'y'}
ARS_URL_DEV = 'https://ars-dev.transltr.io/ars/api/'
ARS_URL_PROD = 'https://ars.transltr.io/ars/api/'
ARS_URL_PATH_MESSAGES = 'messages/'
ARS_URL_PATH_SUBMIT = 'submit'

KEY_CURIE = 'curie'
KEY_FOUND_IN_AGENTS = 'found_in_agents'

SRI_NN_BASE_URL = 'https://nodenormalization-sri.renci.org/1.2/'
SRI_NN_CURIE_IDENTIFER = 'curie'
SRI_NN_NORMALIZED_NODES_ENDPOINT = 'get_normalized_nodes'
SRI_NN_RESPONSE_VALUE_EQUIVALENT_IDENTIFIERS = 'equivalent_identifiers'
SRI_NN_RESPONSE_VALUE_ID = 'id'
SRI_NN_RESPONSE_VALUE_IDENTIFIER = 'identifier'
SRI_NN_RESPONSE_VALUE_LABEL = 'label'

TRAPI_RESP_EDGE_BINDINGS = 'edge_bindings'
TRAPI_RESP_EDGES = 'edges'
TRAPI_RESP_ID = 'id'
TRAPI_RESP_KNOWLEDGE_GRAPH = 'knowledge_graph'
TRAPI_RESP_NODE_BINDINGS = 'node_bindings'
TRAPI_RESP_PREDICATE = 'predicate'
TRAPI_RESP_RESULTS = 'results'

class MiniNodeNormalizer:
    '''A mini version of imProving Agent's SRI Node Normalizer client'''
    def __init__(self) -> None:
        self.normalized_node_cache = {}

    def _check_cache_and_reformat_curies(self, curies):
        cached = {}
        subset = set()

        for curie in curies:
            if curie in self.normalized_node_cache:
                if self.normalized_node_cache[curie] is not None:
                    cached[curie] = self.normalized_node_cache[curie]
                continue
            subset.add(curie)

        return cached, subset

    def get_normalized_nodes(self, curies: Iterable[str]) -> Dict[str, Any]:
        """Returns 'normalized' nodes from the node-normalization
        endpoint for every node curie in `curies`

        Parameters
        ----------
        curies:
            an iterable of CURIEs to search against the get_normalized_nodes
            API endpoint

        Returns
        -------
        Dict[str, Any]:
            JSON response from the node-normalization API
        """
        cached, subset = self._check_cache_and_reformat_curies(curies)
        if not subset:
            return cached

        payload = {SRI_NN_CURIE_IDENTIFER: list(subset)}
        response = requests.get(
            f"{SRI_NN_BASE_URL}/{SRI_NN_NORMALIZED_NODES_ENDPOINT}", params=payload
        )
        if response.status_code == 404:
            for curie in subset:
                self.normalized_node_cache[curie] = None
            empty_results = {curie: None for curie in subset}
            return {**empty_results, **cached}

        if response.status_code != 200:
            response.raise_for_status()

        normalized_nodes = response.json()
        failed_curies = []

        for search_curie, normalized_node in normalized_nodes.items():
            self.normalized_node_cache[search_curie] = normalized_node
            if normalized_node is None:
                failed_curies.append(search_curie)
                continue
            if equivalents := normalized_node.get(SRI_NN_RESPONSE_VALUE_EQUIVALENT_IDENTIFIERS):
                for equivalent in equivalents:
                    self.normalized_node_cache[equivalent[SRI_NN_RESPONSE_VALUE_IDENTIFIER]] = normalized_node

        if failed_curies:
            print(f"Failed to retrieve normalized nodes for {failed_curies}")

        return {**cached, **normalized_nodes}

NN = MiniNodeNormalizer()

    
def _get_equivalent_curies(curies: Iterable[str]) -> Set[str]:
    '''Returns a list of curies that are equivalent to those in
    `curies`. Intended to be used to expand expected curie lists for
    individual nodes in `find_expected_results`
    '''
    equivalent_curies = set()
    normalized_nodes = NN.get_normalized_nodes(curies)
    for search_curie, normalized_node in normalized_nodes.items():
        if not normalized_node:
            equivalent_curies.add(search_curie)
            continue
        _equivalents = normalized_node[SRI_NN_RESPONSE_VALUE_EQUIVALENT_IDENTIFIERS]
        for _equivalent in _equivalents:
            equivalent_curies.add(_equivalent[SRI_NN_RESPONSE_VALUE_IDENTIFIER])

    return equivalent_curies


def _get_name_of_nodes(curies: Iterable[str]) -> Dict[str, str]:
    '''Returns a mapping of curies to their accepted name according to
    the SRI Node Normalizer. If no accepted name can be found, then
    the curie is returned
    
    Parameters:
        curies: an iterable of str curies

    Returns:
        {curie: curie_name}
    '''
    name_mapping = {}
    normalized_nodes = NN.get_normalized_nodes(curies)
    for search_curie, normalized_node in normalized_nodes.items():
        if not normalized_node:
            name_mapping[search_curie] = search_curie
            continue
        name_mapping[search_curie] = normalized_node[SRI_NN_RESPONSE_VALUE_ID][SRI_NN_RESPONSE_VALUE_LABEL]
    
    return name_mapping


def open_query(query_fp: str) -> Dict[str, Any]:
    '''Returns decoded JSON query found at file path `query_fp`'''
    with open(query_fp, 'r') as in_query:
        query = json.load(in_query)
    return query


def print_query(query: Dict[str, Any]) -> None:
    '''Pretty prints a JSON-serializeable `query`'''
    print(json.dumps(query, indent=2))


def _print_arax_url(pk: str) -> None:
    arax_args = {
        ARAX_QUERY_ARG_ID: pk,
        ARAX_QUERY_ARG_SOURCE: ARAX_SOURCE_ARS
    }
    arax_url = f'{ARAX_URL}?{urlencode(arax_args)}'
    print(
        'Request submitted to ARS.\n\n'
        f'Track ARAX results at {arax_url}'
    )


def submit_to_ars(query: Dict[str, Any], ars_url: str = ARS_URL_PROD) -> str:
    '''Submits TRAPI `query` to ARS and returns the PK associated with
    the request

    Parameters
    ----------
    query:
        A valid TRAPI query that compiles to JSON

    ars_url:
        Which ARS URL to use, e.g. dev vs prod
    '''
    r = requests.post(f'{ars_url}{ARS_URL_PATH_SUBMIT}', json=query)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f'Failed request to ARS on {e}')
        return
    
    ars_pk = r.json()['pk']
    _print_arax_url(ars_pk)

    return ars_pk

def _get_ars_result(
    message_id: str,
    ars_url: str = ARS_URL_PROD,
    **kwargs
) -> Dict[str, Any]:
    '''Returns decoded JSON associated with `message_id`
    
    Use kwargs to pass query string args
    '''
    r = requests.get(f'{ars_url}{ARS_URL_PATH_MESSAGES}{message_id}', params=kwargs)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f'Failed to retrieve {message_id} data from ARS on {e}')
        return
    
    return r.json()


def _get_agent_response(child: Dict[str, Any], ars_url: str) -> Tuple[str, Dict[str, Any]]:
    '''Returns the agent name and results from an individual agent in
     the ARS's 'children' field
    
    Parameters
    ----------
    child:
        dict of str -> str, int, or dict[str, str]: one element from the
        ARS's 'children' field in a `_get_ars_result` response
    '''
    agent = child[ARS_RESP_KEY_ACTOR][ARS_RESP_KEY_AGENT]
    try:
        if child[ARS_RESP_KEY_STATUS] == ARS_STATUS_DONE:
            child_response = _get_ars_result(child[ARS_RESP_KEY_MESSAGE], ars_url=ars_url)
            child_message = child_response[ARS_RESP_KEY_FIELDS][ARS_RESP_KEY_DATA][ARS_RESP_KEY_MESSAGE]
        else:
            child_message = {}
    except Exception as e:
        print(f'Error retrieving response from {agent=}')
        child_message = {}
    
    child_results = child_message.get(ARS_RESP_KEY_RESULTS)
    if not child_results:
        child_results = []
    print(f'{agent}:\n  status:{ARS_STATUS_DONE}\n  returned {len(child_results)} results\n')
    return agent, child_message


def get_ars_results(pk: str, ars_url: str = ARS_URL_PROD):
    '''Returns ARS results from the `pk` of a query submitted to the ARS'''
    ars_results = _get_ars_result(pk,  ars_url=ars_url, **ARS_TRACE_PARAMS)
    print(f'ARS query status: {ars_results[ARS_RESP_KEY_STATUS]}')

    agent_results = {}
    for child in ars_results[ARS_RESP_KEY_CHILDREN]:
        agent, message = _get_agent_response(child, ars_url=ars_url)
        agent_results[agent] = message

    return agent_results


def expand_expected_results(
    expected_results: Dict[str, Iterable[str]]
) -> Dict[str, Set[str]]:
    expanded_expected_results = {}
    for qnode_id, expected_curies in expected_results.items():
        expanded_expected_results[qnode_id] = _get_equivalent_curies(expected_curies)
    
    return expanded_expected_results

def _get_predicates_from_agent_response(agent_message: Dict[str, Any]) -> Set[str]:
    '''Returns a mapping of qedge_id -> set of all predicates found in
    the results of a single agent message
    '''
    if TRAPI_RESP_RESULTS not in agent_message:
        return {}
    predicates = defaultdict(set)
    for result in agent_message[TRAPI_RESP_RESULTS]:
        for edge_id, edges in result[TRAPI_RESP_EDGE_BINDINGS].items():
            for edge in edges:
                predicates[edge_id].add(
                    agent_message[TRAPI_RESP_KNOWLEDGE_GRAPH][TRAPI_RESP_EDGES][edge[TRAPI_RESP_ID]][TRAPI_RESP_PREDICATE]
            )

    return predicates

def get_predicates_from_agent_responses(
    ars_results: Dict[str, Any]
) -> Dict[str, Dict[str, Set[str]]]: 
    '''Returns a mapping of qedge_id -> {predicate: {agents-where-found}}
    
    A wrapper on `_get_predicates_from_agent_response` to iterate across
    all agent responses
    '''
    predicates = defaultdict(lambda: defaultdict(set))
    for agent, result_message in ars_results.items():
        agent_predicates = _get_predicates_from_agent_response(result_message)
        if not agent_predicates:
            continue
        for qedge_id, result_predicates in agent_predicates.items():
            for result_predicate in result_predicates:
                predicates[qedge_id][result_predicate].add(agent)
    
    return predicates

def _find_expected_results(
    agent_message: Dict[str, Any],
    expected_results: Dict[str, Iterable[str]],
    any_or_all: str = 'any'
):
    '''Inspects the agent_message for result nodes specified in the
    mapping of expected_results

    Parameters
    ----------
    agent_message:
        TRAPI message from an individual agent
    
    expected_results:
        mapping of qnode_id -> curies that are expected to be found in
        the response

        e.g. for query graph 
        {
          'edges': {
            'e01': {'subject': 'n00', 'object: n01}
          },
          'nodes: {
            'n00': {'ids': [...], 'categories': ['biolink:Gene']},
            'n01': {'categories': ['biolink:Protein']}
          }
        }
        One might expect to find certain protein CURIEs associated with
        node n01, so you'd pass:
        {'n01': ['UniProtKB:1234', 'UniProtKB:4567', ...]}

    any_or_all:
        whether all keys in `expected_results` must be satisfied to
        qualify as 'expected' or if any match is good enough

    Note: CURIEs are normalized to find equivalents
    '''
    agent_results = agent_message.get(ARS_RESP_KEY_RESULTS)
    if not agent_results:
        return []

    found_results = []

    for result in agent_results:
        result_positive_nodes = set()
        for qnode_id, node_bindings in result[TRAPI_RESP_NODE_BINDINGS].items():
            if qnode_id not in expected_results:
                continue
            for node_binding in node_bindings:
                if node_binding[TRAPI_RESP_ID] in expected_results[qnode_id]:
                    result_positive_nodes.add(qnode_id)
        
        if any_or_all == 'all':
            if all([key in result_positive_nodes for key in expected_results.keys()]):
                found_results.append(result)
        else:
            if result_positive_nodes:
                found_results.append(result)
    
    return found_results


def find_expected_results(
    ars_results: Dict[str, Any],
    expected_results: Dict[str, Iterable[str]],
    any_or_all: str = 'any'
) -> Dict[str, Any]:
    '''Returns a mapping of agent_name -> results that contain
    identifiers specified in expected results.
    
    A convenient wrapper on _find_expected_results that iterates through
    all agents.
    '''
    agent_results = {}
    for agent, result_message in ars_results.items():
        agent_results[agent] = _find_expected_results(result_message, expected_results, any_or_all)
    
    return agent_results


def get_all_results(ars_results: Dict[str, Any]) -> Dict[str, Any]:
    '''Returns a mapping of agent name -> the results associated with
    its response to the ARS
    '''
    all_results = {}
    for agent, agent_message in ars_results.items():
        _results = agent_message.get('results')
        if not _results:
            continue
        all_results[agent] = _results
    return all_results


def unify_results(
    agent_results: Dict[str, Any],
    qnode_id_of_interest: str,
    async_: bool = False
) -> Dict[str, Dict[str, Union[str, List[str]]]]:
    unified_results = {}
    for agent, results in agent_results.items():
        if async_ is True:
            agent = f'{agent}-async'
        for result in results:
            nodes_of_interest = result[TRAPI_RESP_NODE_BINDINGS][qnode_id_of_interest]
            entity_name_map = _get_name_of_nodes([node[TRAPI_RESP_ID] for node in nodes_of_interest])
            for entity, name in entity_name_map.items():
                if name in unified_results:
                    unified_results[name][KEY_FOUND_IN_AGENTS].add(agent)
                else:
                    unified_results[name] = {KEY_CURIE: entity, KEY_FOUND_IN_AGENTS: set([agent])}
    
    return unified_results

def print_unified_results(unified_results: Dict[str, Dict[str, Union[str, Set[str]]]]) -> None:
    '''Pretty prints unified_results'''
    for node_name, data in unified_results.items():
        print(f'{node_name}:')
        print(f'  CURIE: {data[KEY_CURIE]}')
        print('  Found in agents:')
        for agent in data[KEY_FOUND_IN_AGENTS]:
            print(f'    {agent}')
        print()


def print_edge_results(
    results: Dict[str, Dict[str, Set[str]]],
    qedge_id_of_interest: str
) -> None:
    '''Pretty prints edge results'''
    for predicate, agents in results[qedge_id_of_interest].items():
        print(f'{predicate}:')
        print('  Found in agents:')
        for agent in agents:
            print(f'    {agent}')
        print()