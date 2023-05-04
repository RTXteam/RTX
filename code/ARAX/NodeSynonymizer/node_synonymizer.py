import ast
import json
import os
import sqlite3
import sys
from collections import defaultdict
from typing import Optional, Union, List, Set

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration


class NodeSynonymizer:

    def __init__(self):
        self.rtx_config = RTXConfiguration()
        self.database_name = self.rtx_config.node_synonymizer_path.split("/")[-1]
        self.database_name = "node_synonymizer_v1.1_KG2.8.0.sqlite"  # TODO: temporary for testing - remove later
        synonymizer_dir = os.path.dirname(os.path.abspath(__file__))
        self.database_path = f"{synonymizer_dir}/{self.database_name}"
        print(f"Connecting to database {self.database_name}, located at {self.database_path}")
        self.db_connection = sqlite3.connect(self.database_path)

    def __del__(self):
        print(f"Closing database connection")
        self.db_connection.close()

    # --------------------------------------- EXTERNAL MAIN METHODS ----------------------------------------------- #

    def get_canonical_curies(self, curies: Optional[Union[str, Set[str], List[str]]] = None,
                             names: Optional[Union[str, Set[str], List[str]]] = None,
                             return_all_categories: bool = False) -> dict:

        # Convert any input values to Set format
        curies_set = self._convert_to_set_format(curies)
        names_set = self._convert_to_set_format(names)
        results_dict = dict()
        results_dict_names = dict()

        if curies_set:
            # Query the synonymizer sqlite database for these identifiers
            sql_query = f"""
                    SELECT N.id, N.cluster_id, C.name, C.category
                    FROM nodes as N
                    INNER JOIN clusters as C on C.cluster_id == N.cluster_id
                    WHERE N.id in ('{self._convert_to_str_format(curies_set)}')"""
            matching_rows = self._execute_sql_query(sql_query)

            # Transform the results into the proper response format
            results_dict = {row[0]: self._create_preferred_node_dict(preferred_id=row[1],
                                                                     preferred_category=row[3],
                                                                     preferred_name=row[2])
                            for row in matching_rows}

        if names_set:
            # Query the synonymizer sqlite database for these names
            sql_query = f"""
                    SELECT N.id, N.name, N.cluster_id, C.name, C.category
                    FROM nodes as N
                    INNER JOIN clusters as C on C.cluster_id == N.cluster_id
                    WHERE N.name in ('{self._convert_to_str_format(names_set)}')"""
            matching_rows = self._execute_sql_query(sql_query)

            # For each input name, pick the cluster that nodes with that exact name most often belong to
            names_to_cluster_counts = defaultdict(lambda: defaultdict(int))
            for row in matching_rows:
                name = row[1]
                cluster_id = row[2]
                names_to_cluster_counts[name][cluster_id] += 1
            names_to_best_cluster_id = {name: max(cluster_counts, key=cluster_counts.get)
                                        for name, cluster_counts in names_to_cluster_counts.items()}

            # Transform the results into the proper response format
            node_ids_to_rows = {row[0]: row for row in matching_rows}
            results_dict_names = {name: self._create_preferred_node_dict(preferred_id=cluster_id,
                                                                         preferred_category=node_ids_to_rows[cluster_id][4],
                                                                         preferred_name=node_ids_to_rows[cluster_id][3])
                                  for name, cluster_id in names_to_best_cluster_id.items()}

        # Merge our results for input curies and input names
        results_dict.update(results_dict_names)

        # Tack on all categories, if asked for (infrequent enough that it's ok to have an extra query for this)
        if return_all_categories:
            cluster_ids = {canonical_info["preferred_curie"]
                           for canonical_info in results_dict.values()}
            sql_query = f"""
                    SELECT N.cluster_id, N.category
                    FROM nodes as N
                    WHERE N.cluster_id in ('{self._convert_to_str_format(cluster_ids)}')"""
            matching_rows = self._execute_sql_query(sql_query)

            # Count up how many members this cluster has with different categories
            clusters_by_category_counts = defaultdict(lambda: defaultdict(int))
            for cluster_id, member_category in matching_rows:
                member_category = self._add_biolink_prefix(member_category)
                clusters_by_category_counts[cluster_id][member_category] += 1

            # Add the counts to our response
            for canonical_info in results_dict.values():
                cluster_id = canonical_info["preferred_curie"]
                category_counts = clusters_by_category_counts[cluster_id]
                canonical_info["all_categories"] = dict(category_counts)

        # Add None values for any unrecognized input values
        unrecognized_input_values = (curies_set.union(names_set)).difference(results_dict)
        for unrecognized_value in unrecognized_input_values:
            results_dict[unrecognized_value] = None

        return results_dict

    def get_equivalent_nodes(self, curies: Optional[Union[str, Set[str], List[str]]],
                             include_unrecognized_curies: bool = True) -> dict:

        # Convert any input curies to Set format
        curies = self._convert_to_set_format(curies)

        # Query the synonymizer sqlite database for these identifiers
        sql_query = f"""
                SELECT N.id, C.member_ids
                FROM nodes as N
                INNER JOIN clusters as C on C.cluster_id == N.cluster_id
                WHERE N.id in ('{self._convert_to_str_format(curies)}')"""
        matching_rows = self._execute_sql_query(sql_query)

        # Transform the results into the proper response format
        results_dict = {row[0]: set(ast.literal_eval(row[1])) for row in matching_rows}

        if include_unrecognized_curies:
            # Add None values for any unrecognized input curies
            unrecognized_curies = curies.difference(results_dict)
            for unrecognized_curie in unrecognized_curies:
                results_dict[unrecognized_curie] = None

        return results_dict

    def get_normalizer_results(self, curies: Optional[Union[str, Set[str], List[str]]]) -> dict:

        # Convert any input curies to Set format
        curies = self._convert_to_set_format(curies)

        # First get all equivalent IDs for each input curie
        equivalent_curies_dict = self.get_equivalent_nodes(curies, include_unrecognized_curies=False)

        # Then get info for all of those equivalent nodes
        all_node_ids = set().union(*equivalent_curies_dict.values())
        sql_query = f"""
                SELECT N.id, N.cluster_id, N.name, N.category, N.major_branch, N.name_sri, N.category_sri, N.name_kg2pre, N.category_kg2pre
                FROM nodes as N
                WHERE N.id in ('{self._convert_to_str_format(all_node_ids)}')"""
        matching_rows = self._execute_sql_query(sql_query)
        nodes_dict = {row[0]: {"identifier": row[0],
                               "category": self._add_biolink_prefix(row[3]),
                               "label": row[2],
                               "major_branch": row[4],
                               "in_sri": row[6] is not None,
                               "name_sri": row[5],
                               "category_sri": self._add_biolink_prefix(row[6]),
                               "in_kg2pre": row[8] is not None,
                               "name_kg2pre": row[7],
                               "category_kg2pre": self._add_biolink_prefix(row[8]),
                               "cluster_id": row[1]} for row in matching_rows}

        # Transform the results into the proper response format
        results_dict = dict()
        for input_curie, equivalent_curies in equivalent_curies_dict.items():
            cluster_id = nodes_dict[input_curie]["cluster_id"]
            cluster_rep = nodes_dict[cluster_id]
            results_dict[input_curie] = {"id": {"identifier": cluster_id,
                                                "name": cluster_rep["label"],
                                                "category": cluster_rep["category"],
                                                "SRI_normalizer_name": cluster_rep["name_sri"],
                                                "SRI_normalizer_category": cluster_rep["category_sri"],
                                                "SRI_normalizer_curie": cluster_id if cluster_rep["category_sri"] else None},
                                         "categories": defaultdict(int),
                                         "nodes": [nodes_dict[equivalent_curie] for equivalent_curie in equivalent_curies]}

        # Do some post-processing (tally up category counts and remove no-longer-needed 'cluster_id' property)
        for input_curie, concept_info_dict in results_dict.items():
            for equivalent_node in concept_info_dict["nodes"]:
                concept_info_dict["categories"][equivalent_node["category"]] += 1
                if "cluster_id" in equivalent_node:
                    del equivalent_node["cluster_id"]

        # Add None values for any unrecognized input curies
        unrecognized_curies = curies.difference(results_dict)
        for unrecognized_curie in unrecognized_curies:
            results_dict[unrecognized_curie] = None

        return results_dict

    # ---------------------------------------- INTERNAL HELPER METHODS -------------------------------------------- #

    @staticmethod
    def _convert_to_str_format(list_or_set: Union[Set[str], List[str]]) -> str:
        preprocessed_list = [item.replace("'", "''") for item in list_or_set]  # Need to escape ' characters for SQL
        list_str = "','".join(preprocessed_list)  # SQL wants ('id1', 'id2') format for string lists
        return list_str

    @staticmethod
    def _convert_to_set_format(some_value: Optional[Union[str, Set[str], List[str]]]) -> set:
        if some_value:
            if isinstance(some_value, set):
                return some_value
            elif isinstance(some_value, list):
                return set(some_value)
            elif isinstance(some_value, str):
                return {some_value}
            else:
                raise ValueError(f"Input is not an allowable data type (list, set, or string)!")
        else:
            return set()

    @staticmethod
    def _add_biolink_prefix(category: Optional[str]) -> Optional[str]:
        if category:
            return f"biolink:{category}"
        else:
            return category

    def _create_preferred_node_dict(self, preferred_id: str, preferred_category: str, preferred_name: Optional[str]) -> dict:
        return {
            "preferred_curie": preferred_id,
            "preferred_name": preferred_name,
            "preferred_category": self._add_biolink_prefix(preferred_category)
        }

    def _execute_sql_query(self, sql_query: str) -> list:
        cursor = self.db_connection.cursor()
        cursor.execute(sql_query)
        matching_rows = cursor.fetchall()
        cursor.close()
        return matching_rows


def main():
    test_curies = ["DOID:14330", "MONDO:0005180", "CHEMBL.COMPOUND:CHEMBL112", "UNICORN"]
    test_names = ["Acetaminophen", "Unicorn", "ACETAMINOPHEN", "Parkinson disease"]
    synonymizer = NodeSynonymizer()
    results = synonymizer.get_canonical_curies(test_curies)
    results = synonymizer.get_equivalent_nodes(test_curies)
    results = synonymizer.get_normalizer_results(test_curies)
    results = synonymizer.get_canonical_curies(names=test_names, curies=test_curies)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
