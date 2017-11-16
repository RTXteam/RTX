# Copyright [2010-2017] Integrative Biomedical Informatics Group, Research Programme on Biomedical Informatics (GRIB) IMIM-UPF
# http://ibi.imim.es/
# Modified by Stephen Ramsey at Oregon State University
###############################################################################

import argparse
import urllib.request, urllib.error, urllib.parse
import functools
import pandas
import io
import CachedMethods
import math

class QueryDisGeNet:
    MAX_PROTS_FOR_GENE = 3   ## maybe we should make this a configurable class variable (SAR)
    MAX_GENES_FOR_DISEASE = 20  ## maybe we should make this a configurable class variable (SAR)
    
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

        binary_data = seq.encode("utf-8")
        req = urllib.request.Request("http://www.disgenet.org/oql")
        res = urllib.request.urlopen(req, binary_data)
        data  = res.read().decode("utf-8")
        res.close()
        ret_data_df = pandas.read_csv(io.StringIO(data), sep="\t").head(QueryDisGeNet.MAX_GENES_FOR_DISEASE)
        uniprot_ids_list = ret_data_df["c2.uniprotId"].tolist()
        gene_names_list = ret_data_df["c2.symbol"].tolist()
        ret_dict = dict(list(zip(uniprot_ids_list, gene_names_list)))
#        ret_data = set(ret_data_df["c2.uniprotId"].tolist()) - {'null'}
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
                            if prot_name is not math.nan:
                                dict_add[prot_name] = gene
#                        dict_add = dict.fromkeys(prots_to_add, gene)  # testing issue #19 SAR
                        ret_dict.update(dict_add)
        return(ret_dict)
                            
    @staticmethod
    def test():
        print(QueryDisGeNet.query_mesh_id_to_uniprot_ids_desc('D016779'))
        print(QueryDisGeNet.query_mesh_id_to_uniprot_ids_desc('D004443'))

if __name__ == '__main__':
    QueryDisGeNet.test()
    
        
