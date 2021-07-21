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

    def get_information_resource_values(self)
        return self.get_edge_attribute_values(attribute_type_id="biolink:InformationResource")



