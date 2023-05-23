import sys
import os
import pandas as pd
import numpy as np
import argparse

def refresh_chemical(curie_list, synonymizer):

    res = synonymizer.get_canonical_curies(curie_list)
    return [(res[curie]['preferred_curie'], res[curie]['preferred_category']) if res[curie] is not None and res[curie]['preferred_category'] in ['biolink:ChemicalEntity', 'biolink:ChemicalMixture', 'biolink:SmallMolecule'] else None for curie in curie_list]

def refresh_gene(curie_list, synonymizer):

    res = synonymizer.get_canonical_curies(curie_list)
    return [(res[curie]['preferred_curie'], res[curie]['preferred_category']) if res[curie] is not None and res[curie]['preferred_category'] in ['biolink:Gene', 'biolink:Protein'] else None for curie in curie_list]

def main():

    parser = argparse.ArgumentParser(description="Refresh DTD model and database", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--synoymizer_folder', type=str, help="Full path of folder containing NodeSynonymizer", default='~/RTX/code/ARAX/NodeSynonymizer/')
    parser.add_argument('--npz_file', type=str, help="Full path of CRG npz file", default='~/work/RTX/code/ARAX/ARAXQuery/Infer/data/xCRG_data/chemical_gene_embeddings_v1.0.KG2.8.0.npz')
    parser.add_argument('--output_filename', type=str, help="Output filename")
    parser.add_argument('--output_folder', type=str, help="Full path of output folder", default='~/work/RTX/code/ARAX/ARAXQuery/Infer/data/xCRG_data/')
    args = parser.parse_args()

    if os.path.isdir(args.synoymizer_folder):
        sys.path.append(args.synoymizer_folder)
        from node_synonymizer import NodeSynonymizer
        synonymizer = NodeSynonymizer()
    else:
        print(f"Error: Not found this folder: {args.synoymizer_folder}")
        exit(0)

    if os.path.isfile(args.npz_file):
        print(f'INFO: Start to refresh {args.npz_file}', flush=True)
        npzfile = np.load(args.npz_file, allow_pickle=True)
        chemical_curies = npzfile['chemical_curies']
        chemical_curie_types = npzfile['chemical_curie_types']
        chemical_embs  = npzfile['chemical_embs']
        gene_curies = npzfile['gene_curies']
        gene_curie_types = npzfile['gene_curie_types']
        gene_embs = npzfile['gene_embs']
        
        print(f'INFO: Refresh chemical', flush=True)
        chemical_curies_list = refresh_chemical(chemical_curies.tolist(), synonymizer)
        selected_index = [index for index, x in enumerate(chemical_curies_list) if x]
        chemical_curies = np.array([chemical_curies_list[i][0] for i in selected_index])
        chemical_curie_types = np.array([chemical_curies_list[i][1] for i in selected_index])
        chemical_embs = chemical_embs[selected_index]
        print(f'INFO: Refresh chemical completed', flush=True)

        print(f'INFO: Refresh gene', flush=True)
        gene_curies_list = refresh_gene(gene_curies.tolist(), synonymizer)
        selected_index = [index for index, x in enumerate(gene_curies_list) if x]
        gene_curies = np.array([gene_curies_list[i][0] for i in selected_index])
        gene_curie_types = np.array([gene_curies_list[i][1] for i in selected_index])
        gene_embs = gene_embs[selected_index]
        print(f'INFO: Refresh gene completed', flush=True)

        output_file = os.path.join(args.output_folder, args.output_filename)
        print(f'INFO: Start to save {output_file}', flush=True)
        np.savez(output_file, chemical_curies=chemical_curies, chemical_curie_types=chemical_curie_types, chemical_embs=chemical_embs, gene_curies=gene_curies, gene_curie_types=gene_curie_types, gene_embs=gene_embs)
        print(f"INFO: Data Refreshed Completed", flush=True)
    else:
        print(f"Error: Not found this file: {args.npz_file}")
        exit(0)

####################################################################################################

if __name__ == "__main__":
    main()