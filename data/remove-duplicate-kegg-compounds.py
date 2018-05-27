import pandas
import requests
import sys

# read the seed_nodes.tsv file


def get_kegg_for_chembl(chembl_id_str):
    url = 'http://mychem.info/v1/chem/' + chembl_id_str
    res = requests.get(url)
    res_kegg = None
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
                        ret_str = res_kegg
    return res_kegg


def do_conversion():
    seed_node_data = pandas.read_csv('seed_nodes.tsv',
                                     sep="\t",
                                     names=['type', 'rtx_name', 'term', 'purpose'],
                                     header=0,
                                     dtype={'rtx_name': str})
    first_row = True

    chemical_substance_terms = set()
    kegg_ids = set()
    
    for index, row in seed_node_data.iterrows():
        entity_type = row['type']
        term = row['term']
        id = row['rtx_name']
        if entity_type == 'chemical_substance':
            chemical_substance_terms.add(term)
            kegg_id = get_kegg_for_chembl(id)
            if kegg_id is not None:
                if (type(kegg_id) == str):
                    kegg_ids.add(kegg_id)
                else:
                    if (type(kegg_id) == list):
                        kegg_ids.update(kegg_id)
        else:
            if entity_type == 'metabolite':
                if term.lower() in chemical_substance_terms:
                    continue
                else:
                    # need to check if the ID maps
                    assert id.startswith('KEGG:')
                    kegg_compound_id = id.split('KEGG:')[1]
                    if kegg_compound_id in kegg_ids:
                        continue
        print(entity_type + "\t" + id + "\t" + term + "\t" + row['purpose'])

do_conversion()
