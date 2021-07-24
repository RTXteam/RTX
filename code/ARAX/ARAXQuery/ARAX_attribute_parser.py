import os
import sys
from ARAX_response import ARAXResponse


class ARAXAttributeParser:
    def __init__(self, response, message):
        self.response = response
        self.message = message

    def get_edge_attribute_values(self, attribute_type_id=None, original_attribute_name=None):
        attribute_values = set()
        for edge_key, edge in self.message.knowledge_graph.edges.items():
            if hasattr(edge, 'attributes'):
                if edge.attributes:
                    for attribute in edge.attributes:
                        if attribute_type_id is not None and hasattr(attribute, "attribute_type_id"):
                            if attribute.attribute_type_id == attribute_type_id:
                                attribute_values.add(attribute.value)
                        if original_attribute_name is not None and hasattr(attribute, "original_attribute_name"):
                            if attribute.original_attribute_name == original_attribute_name:
                                attribute_values.add(attribute.value)
        return attribute_values

    def get_information_resource_values(self):
        return self.get_edge_attribute_values(attribute_type_id="biolink:InformationResource")


    def summarize_provenance_info(self):
        provenance_information = { 'n_sources': 0, 'provenance_counts': {}, 'predicate_counts': {} }
        sources = {}
        information_type_ids = {
            'biolink:knowledge_source' : True,
            'biolink:original_knowledge_source': True,
            'biolink:aggregator_knowledge_source': True,
            'biolink:primary_knowledge_source': True,
            'biolink:supporting_data_source': True
        }
 
        #### If message is in dict form, just work with that instead of converting it first
        if isinstance(self.message,dict):
            if 'knowledge_graph' not in self.message or self.message['knowledge_graph'] is None:
                return provenance_information
            if 'edges' not in self.message['knowledge_graph'] or self.message['knowledge_graph']['edges'] is None:
                return provenance_information
            for edge_key, edge in self.message['knowledge_graph']['edges'].items():
                found_provenance = False
                predicate = edge['predicate']
                if predicate not in provenance_information['predicate_counts']:
                    provenance_information['predicate_counts'][predicate] = 0
                provenance_information['predicate_counts'][predicate] += 1
                if 'attributes' in edge and edge['attributes'] is not None:
                    for attribute in edge['attributes']:
                        if 'attribute_type_id' in attribute and attribute['attribute_type_id'] is not None and attribute['attribute_type_id'] in information_type_ids and 'value' in attribute:
                            value = attribute['value']
                            if value is None:
                                value = '???'
                            sources[f"{value}"] = True
                            label = f"{predicate} --> {attribute['attribute_type_id']} = {value}"
                            if label not in provenance_information['provenance_counts']:
                                provenance_information['provenance_counts'][label] = [ predicate, attribute['attribute_type_id'], value, 0 ]
                            provenance_information['provenance_counts'][label][3] += 1
                            found_provenance = True
                if not found_provenance:
                    label = f"{predicate} --> no provenance"
                    if label not in provenance_information['provenance_counts']:
                        provenance_information['provenance_counts'][label] = [ predicate, '-', 'no provenance', 0 ]
                    provenance_information['provenance_counts'][label][3] += 1
            provenance_information['n_sources'] = len(sources)

        #### Else assume it is objects
        else:
            for edge_key, edge in self.message.knowledge_graph.edges.items():
                found_provenance = False
                if hasattr(edge, 'attributes'):
                    if edge.attributes:
                        for attribute in edge.attributes:
                            if hasattr(attribute, "attribute_type_id") and attribute.attribute_type_id is not None and attribute.attribute_type_id in information_type_ids:
                                value = attribute.value
                                if value is None:
                                    value = '???'
                                label = f"{attribute.attribute_type_id} = {value}"
                                if label not in provenance_information:
                                    provenance_information[label] = 0
                                provenance_information[label] += 1
                                found_provenance = True
                if not found_provenance:
                    label = 'edges with no provenance'
                    if label not in provenance_information:
                        provenance_information[label] = 0
                    provenance_information[label] += 1

        return provenance_information


