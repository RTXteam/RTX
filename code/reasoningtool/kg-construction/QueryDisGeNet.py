# Copyright [2010-2017] Integrative Biomedical Informatics Group, Research Programme on Biomedical Informatics (GRIB) IMIM-UPF
# http://ibi.imim.es/
# Modified by Stephen Ramsey at Oregon State University
###############################################################################
""" This module defines the class QueryDisGeNet which is designed to query
descriptions according to the mesh ids.
"""

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Yao Yao', 'Zheng Liu']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import pandas
import io
import math
import requests
import sys
import functools
import CachedMethods

class QueryDisGeNet:
    MAX_PROTS_FOR_GENE = 3   ## maybe we should make this a configurable class variable (SAR)
    MAX_GENES_FOR_DISEASE = 20  ## maybe we should make this a configurable class variable (SAR)
    SPARQL_ENDPOINT_URL = 'http://www.disgenet.org/oql'
    TIMEOUT_SEC = 120

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def query_mesh_id_to_uniprot_ids_desc(mesh_id):
        ent = 'disease'
        id = 'mesh'
        STR = "c1.MESH = '"
        intfield = mesh_id
        seq = ( """
        DEFINE
        c0='/data/gene_disease_summary',
	c1='/data/diseases',
	c2='/data/genes',
	c4='/data/sources'
        ON
           'http://www.disgenet.org/web/DisGeNET'
        SELECT
        c1 (diseaseId, name, diseaseClassName, STY, MESH, OMIM, type ),
	c2 (geneId, symbol,   uniprotId, description, pantherName ),
	c0 (score, EI, Npmids, Nsnps)

        FROM
            c0
        WHERE
            (
                """ + STR +  mesh_id+"""'
            AND
                c4 = 'ALL'
            )
        ORDER BY
            c0.score DESC""" ); #

        binary_data = seq.encode('utf-8')
        url_str = QueryDisGeNet.SPARQL_ENDPOINT_URL

        try:
            res = requests.post(url_str, data=binary_data, timeout=QueryDisGeNet.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url_str, sys.stderr)
            print('Timeout in QueryDisGeNet for URL: ' + url_str, file=sys.stderr)
            return dict()

        status_code = res.status_code

        if status_code != 200:
            print(url_str, sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url_str, file=sys.stderr)
            return dict()

        if len(res.content) == 0:
            print(url_str, file=sys.stderr)
            print('Empty response from URL!', file=sys.stderr)
            return dict()

        ret_data_df = pandas.read_csv(io.StringIO(res.content.decode('utf-8')), sep='\t').head(QueryDisGeNet.MAX_GENES_FOR_DISEASE)
        uniprot_ids_list = ret_data_df['c2.uniprotId'].tolist()
        gene_names_list = ret_data_df['c2.symbol'].tolist()
        ret_dict = dict(list(zip(uniprot_ids_list, gene_names_list)))
        for prot in ret_dict.copy().keys():
            if type(prot)==str:
                if '.' in prot or ';' in prot:
                    gene = ret_dict[prot]
                    del ret_dict[prot]
                    prot.replace('.', '')
                    prots_to_add = prot.split(';')
                    if len(prots_to_add) > QueryDisGeNet.MAX_PROTS_FOR_GENE:
                        prots_to_add = prots_to_add[0:QueryDisGeNet.MAX_PROTS_FOR_GENE]
                        dict_add = dict()
                        for prot_name in prots_to_add:
                            if type(prot_name) == str:
                                dict_add[prot_name] = gene
                        ret_dict.update(dict_add)
            else:  ## this is a math.nan
                del ret_dict[prot]
        return(ret_dict)


if __name__ == '__main__':
    print(QueryDisGeNet.query_mesh_id_to_uniprot_ids_desc('D016779'))
    print(QueryDisGeNet.query_mesh_id_to_uniprot_ids_desc('D004443'))
