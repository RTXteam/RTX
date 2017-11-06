# Copyright [2010-2017] Integrative Biomedical Informatics Group, Research Programme on Biomedical Informatics (GRIB) IMIM-UPF
# Modified by Stephen Ramsey at Oregon State University
# http://ibi.imim.es/
# contact for technical questions support@disgenet.org
# creator: janet.pinero@upf.edu  
# Script to query disgenet using a list of genes or diseases
# requires as input the gene or disease list in a file 
# the output file name
# the type of entity (gene or disease)
# the type of identifier 
###############################################################################

import argparse
import urllib.request, urllib.error, urllib.parse
import sys
import pandas
import io

class QueryDisGeNet:
    @staticmethod
    def query_mesh_id_to_uniprot_ids(mesh_id):
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
        ret_data = set(pandas.read_csv(io.StringIO(data), sep="\t")["c2.uniprotId"].tolist()) - {'null'}
        for prot in ret_data.copy():
            if '.' in prot:
                ret_data.remove(prot)
                ret_data.add(prot.split('.')[0])
            if ';' in prot:
                ret_data.remove(prot)
                ret_data |= set(prot.split(';'))
        
        return(ret_data)

    
    @staticmethod
    def test():
        print(QueryDisGeNet.query_mesh_id_to_uniprot_ids('D016779'))

if "--test" in set(sys.argv):
    QueryDisGeNet.test()
    
        
