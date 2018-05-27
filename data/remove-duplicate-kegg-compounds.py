import pandas
import requests
import sys

# read the seed_nodes.tsv file


def get_kegg_for_chembl(chembl_id_str):
    url = 'http://mychem.info/v1/chem/' + chembl_id_str
    res = requests.get(url)
    res_kegg = None
    res_brand_names = None
    if res is not None:
        status_code = res.status_code
        if status_code != 200:
            print("status code " + str(status_code) + " for URL: " + url, file=sys.stderr)
            sys.exit()
        else:
            res_json = res.json()
            if res_json is not None:
                res_chebi = res_json.get("chebi")
                if res_chebi is not None:
                    res_kegg = res_chebi.get("kegg_compound_database_links", None)
                    if res_kegg is not None:
                        res_brand_names = res_chebi.get("brand_names", None)

    return [res_kegg, res_brand_names]


def do_conversion():
    seed_node_data = pandas.read_csv('seed_nodes.tsv',
                                     sep="\t",
                                     names=['type', 'rtx_name', 'term', 'purpose'],
                                     header=0,
                                     dtype={'rtx_name': str})

    chemical_substance_terms = set()
    kegg_ids = dict()

    for index, row in seed_node_data.iterrows():
        entity_type = row['type']
        term = row['term']
        id = row['rtx_name']
        if entity_type == 'chemical_substance':
            chemical_substance_terms.add(term)
            kegg_id, brand_names = get_kegg_for_chembl(id)
            if kegg_id is not None:
                if (type(kegg_id) == str):
                    kegg_ids[kegg_id] = brand_names
                else:
                    if (type(kegg_id) == list):
                        for single_id in kegg_id:
                            kegg_ids[single_id] = brand_names
        else:
            if entity_type == 'metabolite':
                # need to check if the ID maps
                assert id.startswith('KEGG:')
                kegg_compound_id = id.split('KEGG:')[1]
                if kegg_compound_id in kegg_ids and kegg_ids[kegg_compound_id] is not None:
                    continue
        print(entity_type + "\t" + id + "\t" + term + "\t" + row['purpose'])

do_conversion()
