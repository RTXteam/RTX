import numpy as np
import pandas as pd
import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-i","--input", type=str, help="The full path of graphsage output folder")
parser.add_argument("-o","--output", type=str, help="The full path of output file", default="./graph.emb")
args = parser.parse_args()

if __name__ == "__main__":

    # change to the current path
    current_path = os.path.split(os.path.realpath(__file__))[0]
    os.chdir(current_path)

    # check the input arguments
    npy_file = args.input + '/val.npy'
    txt_file = args.input + '/val.txt'

    if not os.path.exists(os.path.realpath(npy_file)):
        sys.exit("Error Occurred! Can't find the val.npy file. Please provide the correct path of graphsage output folder.")
    else:
        data = np.load(npy_file)
    if not os.path.exists(os.path.realpath(txt_file)):
        sys.exit("Error Occurred! Can't find the val.txt file. Please provide the correct path of graphsage output folder.")
    else:
        node_id =pd.read_csv(open(txt_file,'r'),header=None)
    if args.output == "/graph.emb":
        outpath = current_path + '/graph.emb'
    else:
        outpath = os.path.realpath(args.output)

    id_vec = pd.concat([node_id,pd.DataFrame(data)],axis=1)
    firstline = list(id_vec.iloc[:, 1:].shape)

    with open(outpath,'w') as out:
        s = ' '.join([str(i) for i in firstline])
        out.writelines('%s\n' % s)
    id_vec.to_csv(outpath, sep=' ', mode='a', header=False, index=False)



