import ast
import os
import sqlite3
import sys
from collections import defaultdict
from typing import Optional, Union, Sequence, List, Set

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

    def get_canonical_curies(self, curies: Optional[Union[str, Set[str], List[str]]],
                             return_all_categories: bool = False) -> dict:

        # Convert any input curies to Set format
        curies = self._convert_input_to_set_format(curies)

        # Query the synonymizer sqlite database for these identifiers
        sql_query = f"""
                SELECT N.id, N.cluster_id, C.name, C.category
                FROM nodes as N
                INNER JOIN clusters as C on C.cluster_id == N.cluster_id
                WHERE N.id in ('{self._convert_to_str_format(curies)}')"""
        matching_rows = self._execute_sql_query(sql_query)

        # Transform the results into the proper response format
        results_dict = {row[0]: {
            "preferred_curie": row[1],
            "preferred_name": row[2],
            "preferred_category": row[3]
        } for row in matching_rows}

        # Grab all categories if that was asked for (infrequent enough that it's ok to have an extra query for this)
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

        # Add None values for any unrecognized input curies
        unrecognized_curies = curies.difference(results_dict)
        for unrecognized_curie in unrecognized_curies:
            results_dict[unrecognized_curie] = None

        return results_dict

    def get_equivalent_nodes(self, curies: Optional[Union[str, Set[str], List[str]]]) -> dict:

        # Convert any input curies to Set format
        curies = self._convert_input_to_set_format(curies)

        # Query the synonymizer sqlite database for these identifiers
        sql_query = f"""
                SELECT N.id, C.member_ids
                FROM nodes as N
                INNER JOIN clusters as C on C.cluster_id == N.cluster_id
                WHERE N.id in ('{self._convert_to_str_format(curies)}')"""
        matching_rows = self._execute_sql_query(sql_query)

        # Transform the results into the proper response format
        results_dict = {row[0]: set(ast.literal_eval(row[1])) for row in matching_rows}

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
    def _convert_input_to_set_format(input_values: Optional[Union[str, Set[str], List[str]]]) -> set:
        if input_values:
            if isinstance(input_values, set) or isinstance(input_values, list):
                return set(input_values)
            elif isinstance(input_values, str):
                return {input_values}
            else:
                raise ValueError(f"Input is not an allowable data type (list, set, or string)!")
        else:
            return set()

    @staticmethod
    def _add_biolink_prefix(category: str) -> str:
        return f"biolink:{category}"

    def _execute_sql_query(self, sql_query: str) -> list:
        cursor = self.db_connection.cursor()
        cursor.execute(sql_query)
        matching_rows = cursor.fetchall()
        cursor.close()
        return matching_rows


def main():
    test_curies = ["DOID:14330", "CHEMBL.COMPOUND:CHEMBL112", "UNICORN"]
    synonymizer = NodeSynonymizer()
    results = synonymizer.get_canonical_curies(test_curies)
    results = synonymizer.get_equivalent_nodes(test_curies)
    print(results)


if __name__ == "__main__":
    main()
