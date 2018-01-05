'''Returns the Normalized Google semantic distance between two string MeSH terms

   Usage:    python3 CmdPubMedNGD.py term1 term2

   Example:  python3 CmdPubMedNGD.py atherosclerosis hypercholesterolemia
'''
__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import argparse
import math
import json
from QueryNCBIeUtils import QueryNCBIeUtils

def main():
    parser = argparse.ArgumentParser(description="Returns the Normalized Google semantic distance between two string MeSH terms",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('terms', metavar='terms', type=str, nargs=2, help='two string arguments; must be MeSH terms')
    args = parser.parse_args()
    mesh_terms = args.terms
    ngd = QueryNCBIeUtils.normalized_google_distance(*mesh_terms)
    res_dict = dict()
    res_dict['value'] = ngd
    
    if math.isnan(ngd):
        res_dict['status'] = 'unsuccessful'
        if not QueryNCBIeUtils.is_mesh_term(mesh_terms[0]):
            res_dict['status'] += '; Term 1 is not a valid MeSH term'
        if not QueryNCBIeUtils.is_mesh_term(mesh_terms[1]):
            res_dict['status'] += '; Term 2 is not a valid MeSH term'
    else:
        res_dict['status'] = 'success'
    print(json.dumps(res_dict))
    
if __name__ == "__main__":
    main()

