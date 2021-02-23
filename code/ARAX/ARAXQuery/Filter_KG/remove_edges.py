# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import sys
import os
import traceback
import numpy as np

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute as EdgeAttribute

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/kg-construction/")
from NormGoogleDistance import NormGoogleDistance as NGD


class RemoveEdges:

    #### Constructor
    def __init__(self, response, message, edge_params):
        self.response = response
        self.message = message
        self.edge_parameters = edge_params

    def check_kg_nodes(self):
        qids = {}
        for key, node in self.message.query_graph.nodes.items():
            qids[key] = 0
        for key, node in self.message.knowledge_graph.nodes.items():
            if node.qnode_keys is not None:
                for qid in node.qnode_keys:
                    qids[qid] += 1
        for k, v in qids.items():
            if v == 0:
                self.response.error(f"Fiter removed all of the nodes in the knowledge graph with the qnode id {k}", error_code="RemovedQueryNode")


    def remove_edges_by_predicate(self):
        """
        Iterate over all the edges in the knowledge graph, remove any edges matching the discription provided.
        :return: response
        """
        self.response.debug(f"Removing Edges")
        self.response.info(f"Removing edges from the knowledge graph matching the specified predicate")
        edge_params = self.edge_parameters
        try:
            edges_to_remove = set()
            node_keys_to_remove = {}
            edge_qid_dict = {}
            for key, q_edge in self.message.query_graph.edges.items():
                edge_qid_dict[key] = {'subject':q_edge.subject, 'object':q_edge.object}
            # iterate over the edges find the edges to remove
            for key, edge in self.message.knowledge_graph.edges.items():
                if edge.predicate == edge_params['edge_predicate']:
                    edges_to_remove.add(key)
                    if edge_params['remove_connected_nodes']:
                        for qedge_key in edge.qedge_keys:
                            if edge.subject not in node_keys_to_remove:
                                node_keys_to_remove[edge.subject] = {edge_qid_dict[qedge_key]['subject']}
                            else:
                                node_keys_to_remove[edge.subject].add(edge_qid_dict[qedge_key]['subject'])
                            if edge.object not in node_keys_to_remove:
                                node_keys_to_remove[edge.object] = {edge_qid_dict[qedge_key]['object']}
                            else:
                                node_keys_to_remove[edge.object].add(edge_qid_dict[qedge_key]['object'])
            if edge_params['remove_connected_nodes']:
                self.response.debug(f"Removing Nodes")
                self.response.info(f"Removing connected nodes and their edges from the knowledge graph")
                i = 0
                nodes_to_remove = set()
                # iterate over nodes find adjacent connected nodes
                for key, node in self.message.knowledge_graph.nodes.items():
                    if key in node_keys_to_remove:
                        if 'qnode_key' in edge_params:
                            if node.qnode_keys is not None:
                                if edge_params['qnode_key'] in node.qnode_keys:
                                    if len(node.qnode_keys) == 1:
                                        nodes_to_remove.add(key)
                                    else:
                                        node.qnode_keys.remove(edge_params['qnode_key'])
                                else:
                                    del node_keys_to_remove[key]
                            else:
                                del node_keys_to_remove[key]
                        else:
                            if len(node.qnode_keys) == 1:
                                nodes_to_remove.add(key)
                            else:
                                for node_key in node_keys_to_remove[key]:
                                    node.qnode_keys.remove(node_key)
                                if len(node.qnode_keys) == 0:
                                    nodes_to_remove.add(key)
                # remove connected nodes
                #self.message.knowledge_graph.nodes = [val for idx,val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
                for key in nodes_to_remove:
                    del self.message.knowledge_graph.nodes[key]
                # iterate over edges find edges connected to the nodes
                for key, edge in self.message.knowledge_graph.edges.items():
                    if edge.subject in node_keys_to_remove or edge.object in node_keys_to_remove:
                        edges_to_remove.add(key)
                self.check_kg_nodes()
            # remove edges
            #self.message.knowledge_graph.edges = [val for idx,val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code = error_type.__name__)
            self.response.error(f"Something went wrong removing edges from the knowledge graph")
        else:
            self.response.info(f"Edges successfully removed")

        return self.response

    def remove_edges_by_property(self):
        """
        Iterate over all the edges in the knowledge graph, remove any edges matching the discription provided.
        :return: response
        """
        self.response.debug(f"Removing Edges")
        self.response.info(f"Removing edges from the knowledge graph matching the specified property")
        edge_params = self.edge_parameters
        try:
            edges_to_remove = set()
            node_keys_to_remove = {}
            edge_qid_dict = {}
            for key, q_edge in self.message.query_graph.edges.items():
                edge_qid_dict[key] = {'subject':q_edge.subject, 'object':q_edge.object}
            # iterate over the edges find the edges to remove
            for key, edge in self.message.knowledge_graph.edges.items():
                edge_dict = edge.to_dict()
                # TRAPI1.0 hack to allow filtering by old properties that are now attributes
                if hasattr(edge, 'attributes'):
                    for attribute in edge.attributes:
                        if attribute.name not in edge_dict:
                            edge_dict[attribute.name] = attribute.value
                if type(edge_dict[edge_params['edge_property']]) == list:
                    if edge_params['property_value'] in edge_dict[edge_params['edge_property']]:
                        edges_to_remove.add(key)
                        if edge_params['remove_connected_nodes']:
                            for qedge_key in edge.qedge_keys:
                                if edge.subject not in node_keys_to_remove:
                                    node_keys_to_remove[edge.subject] = {edge_qid_dict[qedge_key]['subject']}
                                else:
                                    node_keys_to_remove[edge.subject].add(edge_qid_dict[qedge_key]['subject'])
                                if edge.object not in node_keys_to_remove:
                                    node_keys_to_remove[edge.object] = {edge_qid_dict[qedge_key]['object']}
                                else:
                                    node_keys_to_remove[edge.object].add(edge_qid_dict[qedge_key]['object'])
                else:
                    if edge_dict[edge_params['edge_property']] == edge_params['property_value']:
                        edges_to_remove.add(key)
                        if edge_params['remove_connected_nodes']:
                            for qedge_key in edge.qedge_keys:
                                if edge.subject not in node_keys_to_remove:
                                    node_keys_to_remove[edge.subject] = {edge_qid_dict[qedge_key]['subject']}
                                else:
                                    node_keys_to_remove[edge.subject].add(edge_qid_dict[qedge_key]['subject'])
                                if edge.object not in node_keys_to_remove:
                                    node_keys_to_remove[edge.object] = {edge_qid_dict[qedge_key]['object']}
                                else:
                                    node_keys_to_remove[edge.object].add(edge_qid_dict[qedge_key]['object'])
            if edge_params['remove_connected_nodes']:
                self.response.debug(f"Removing Nodes")
                self.response.info(f"Removing connected nodes and their edges from the knowledge graph")
                nodes_to_remove = set()
                # iterate over nodes find adjacent connected nodes
                for key, node in self.message.knowledge_graph.nodes.items():
                    if key in node_keys_to_remove:
                        if 'qnode_key' in edge_params:
                            if node.qnode_keys is not None:
                                if edge_params['qnode_key'] in node.qnode_keys:
                                    if len(node.qnode_keys) == 1:
                                        nodes_to_remove.add(key)
                                    else:
                                        node.qnode_keys.remove(edge_params['qnode_key'])
                                else:
                                    del node_keys_to_remove[key]
                            else:
                                del node_keys_to_remove[key]
                        else:
                            if len(node.qnode_keys) == 1:
                                nodes_to_remove.add(key)
                            else:
                                for node_key in node_keys_to_remove[key]:
                                    node.qnode_keys.remove(node_key)
                                if len(node.qnode_keys) == 0:
                                    nodes_to_remove.add(key)
                # remove connected nodes
                #self.message.knowledge_graph.nodes = [val for idx,val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
                for key in nodes_to_remove:
                    del self.message.knowledge_graph.nodes[key]
                # iterate over edges find edges connected to the nodes
                for key, edge in self.message.knowledge_graph.edges.items():
                    if edge.subject in node_keys_to_remove or edge.object in node_keys_to_remove:
                        edges_to_remove.add(key)
                self.check_kg_nodes()
            # remove edges
            #self.message.knowledge_graph.edges = [val for idx,val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code = error_type.__name__)
            self.response.error(f"Something went wrong removing edges from the knowledge graph")
        else:
            self.response.info(f"Edges successfully removed")

        return self.response

    def remove_edges_by_attribute(self):
        """
        Iterate over all the edges in the knowledge graph, remove any edges matching with the attribute provided.
        :return: response
        """
        self.response.debug(f"Removing Edges")
        self.response.info(f"Removing edges from the knowledge graph with the specified attribute values")
        edge_params = self.edge_parameters
        try:
            if edge_params['direction'] == 'above':
                def compare(x, y):
                    return x > y
            elif edge_params['direction'] == 'below':
                def compare(x, y):
                    return x < y

            edges_to_remove = set()
            node_keys_to_remove = {}
            edge_qid_dict = {}
            for key, q_edge in self.message.query_graph.edges.items():
                edge_qid_dict[key] = {'subject':q_edge.subject, 'object':q_edge.object}
            # iterate over the edges find the edges to remove
            for key, edge in self.message.knowledge_graph.edges.items():  # iterate over the edges
                if hasattr(edge, 'attributes'):  # check if they have attributes
                    if edge.attributes:  # if there are any edge attributes
                        for attribute in edge.attributes:  # for each attribute
                            if attribute.name == edge_params['edge_attribute']:  # check if it's the desired one
                                if compare(float(attribute.value), edge_params['threshold']):  # check if it's above/below the threshold
                                    edges_to_remove.add(key)  # mark it to be removed
                                    if edge_params['remove_connected_nodes']:  # if you want to remove the connected nodes, mark those too
                                        for qedge_key in edge.qedge_keys:
                                            if edge.subject not in node_keys_to_remove:
                                                node_keys_to_remove[edge.subject] = {edge_qid_dict[qedge_key]['subject']}
                                            else:
                                                node_keys_to_remove[edge.subject].add(edge_qid_dict[qedge_key]['subject'])
                                            if edge.object not in node_keys_to_remove:
                                                node_keys_to_remove[edge.object] = {edge_qid_dict[qedge_key]['object']}
                                            else:
                                                node_keys_to_remove[edge.object].add(edge_qid_dict[qedge_key]['object'])
            if edge_params['remove_connected_nodes']:
                self.response.debug(f"Removing Nodes")
                self.response.info(f"Removing connected nodes and their edges from the knowledge graph")
                nodes_to_remove = set()
                # iterate over nodes find adjacent connected nodes
                for key, node in self.message.knowledge_graph.nodes.items():
                    if key in node_keys_to_remove:
                        if 'qnode_key' in edge_params:
                            if node.qnode_keys is not None:
                                if edge_params['qnode_key'] in node.qnode_keys:
                                    if len(node.qnode_keys) == 1:
                                        nodes_to_remove.add(key)
                                    else:
                                        node.qnode_keys.remove(edge_params['qnode_key'])
                                else:
                                    del node_keys_to_remove[key]
                            else:
                                del node_keys_to_remove[key]
                        else:
                            if len(node.qnode_keys) == 1:
                                nodes_to_remove.add(key)
                            else:
                                for node_key in node_keys_to_remove[key]:
                                    node.qnode_keys.remove(node_key)
                                if len(node.qnode_keys) == 0:
                                    nodes_to_remove.add(key)
                # remove connected nodes
                #self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
                for key in nodes_to_remove:
                    del self.message.knowledge_graph.nodes[key]
                #i = 0
                c = 0
                # iterate over edges find edges connected to the nodes
                for key, edge in self.message.knowledge_graph.edges.items():
                    if edge.subject in node_keys_to_remove or edge.object in node_keys_to_remove:
                        edges_to_remove.add(key)
                    else:
                        c += 1
                    #i += 1
                self.check_kg_nodes()
            # remove edges
            #self.message.knowledge_graph.edges = [val for idx,val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong removing edges from the knowledge graph")
        else:
            self.response.info(f"Edges successfully removed")

        return self.response

    def remove_edges_by_stats(self):
        """
        Iterate over all the edges in the knowledge graph, remove any edges matching with the attribute provided.
        :return: response
        """
        self.response.debug(f"Removing Edges")
        self.response.info(f"Removing edges from the knowledge graph with the specified attribute values")
        edge_params = self.edge_parameters
        try:
            edges_to_remove = set()
            node_keys_to_remove = {}
            edge_qid_dict = {}
            for key, q_edge in self.message.query_graph.edges.items():
                edge_qid_dict[key] = {'subject':q_edge.subject, 'object':q_edge.object}
            values = []
            # iterate over the edges find the edges to remove
            for key, edge in self.message.knowledge_graph.edges.items():  # iterate over the edges
                if hasattr(edge, 'attributes'):  # check if they have attributes
                    if edge.attributes:  # if there are any edge attributes
                        for attribute in edge.attributes:  # for each attribute
                            if attribute.name == edge_params['edge_attribute']:  # check if it's the desired one
                                values.append((key,float(attribute.value), edge.subject, edge.object))
            if len(values) > 0:
                #print(edge_params)
                if edge_params['stat'] == 'n':
                    #vals = [x[1] for x in values]
                    #print(np.min(vals),np.max(vals))
                    values.sort(key=lambda x:x[1])
                    if edge_params['top']:
                        values.reverse()
                    values = values[edge_params['threshold']:]
                    #vals = [x[1] for x in values]
                    #print(np.min(vals),np.max(vals))
                elif edge_params['stat'] == 'std':
                    vals = [x[1] for x in values]
                    #print(np.min(vals),np.max(vals))
                    mean = np.mean(vals)
                    std = np.std(vals)
                    #print(mean)
                    #print(std)
                    if edge_params['top']:
                        i = 1 * edge_params['threshold']
                    else:
                        i = -1 * edge_params['threshold']
                    val = mean + i*std
                    #print(val)
                    if edge_params['direction'] == 'above':
                        values = [x for x in values if x[1]>val]
                    elif edge_params['direction'] == 'below':
                        values = [x for x in values if x[1]<val]
                    #vals = [x[1] for x in values]
                    #print(np.min(vals),np.max(vals))
                elif edge_params['stat'] == 'percentile':
                    vals = [x[1] for x in values]
                    val = np.percentile(vals, edge_params['threshold'], interpolation='linear')
                    if edge_params['direction'] == 'above':
                        values = [x for x in values if x[1]>val]
                    elif edge_params['direction'] == 'below':
                        values = [x for x in values if x[1]<val]

            for edge in values: # here edge = (edge index, value, subject id, object id)
                edges_to_remove.add(edge[0])  # mark it to be removed
                if edge_params['remove_connected_nodes']:  # if you want to remove the connected nodes, mark those too
                    for qedge_key in edge.qedge_keys:
                        if edge.subject not in node_keys_to_remove:
                            node_keys_to_remove[edge[2]] = {edge_qid_dict[qedge_key]['subject']}
                        else:
                            node_keys_to_remove[edge[2]].add(edge_qid_dict[qedge_key]['subject'])
                        if edge.object not in node_keys_to_remove:
                            node_keys_to_remove[edge[3]] = {edge_qid_dict[qedge_key]['object']}
                        else:
                            node_keys_to_remove[edge[3]].add(edge_qid_dict[qedge_key]['object'])

            if edge_params['remove_connected_nodes']:
                self.response.debug(f"Removing Nodes")
                self.response.info(f"Removing connected nodes and their edges from the knowledge graph")
                nodes_to_remove = set()
                # iterate over nodes find adjacent connected nodes
                for key, node in self.message.knowledge_graph.nodes.items():
                    if key in node_keys_to_remove:
                        if 'qnode_key' in edge_params:
                            if node.qnode_keys is not None:
                                if edge_params['qnode_key'] in node.qnode_keys:
                                    if len(node.qnode_keys) == 1:
                                        nodes_to_remove.add(key)
                                    else:
                                        node.qnode_keys.remove(edge_params['qnode_key'])
                                else:
                                    del node_keys_to_remove[key]
                            else:
                                del node_keys_to_remove[key]
                        else:
                            if len(node.qnode_keys) == 1:
                                nodes_to_remove.add(key)
                            else:
                                for node_key in node_keys_to_remove[key]:
                                    node.qnode_keys.remove(node_key)
                                if len(node.qnode_keys) == 0:
                                    nodes_to_remove.add(key)
                # remove connected nodes
                #self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
                for key in nodes_to_remove:
                    del self.message.knowledge_graph.nodes[key]
                c = 0
                # iterate over edges find edges connected to the nodes
                for key, edge in self.message.knowledge_graph.edges.items():
                    if edge.subject in node_keys_to_remove or edge.object in node_keys_to_remove:
                        edges_to_remove.add(key)
                    else:
                        c += 1
                self.check_kg_nodes()
            # remove edges
            #self.message.knowledge_graph.edges = [val for idx,val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong removing edges from the knowledge graph")
        else:
            self.response.info(f"Edges successfully removed")

        return self.response
