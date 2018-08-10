import pandas
import argparse
import ast

# Load arguments from the command line
parser = argparse.ArgumentParser()
parser.add_argument("--tp", type=str, help="The filename or path to the true positive csv", default='')
parser.add_argument("--tn", type=str, help="The filename or path to the true positive csv", default='')
parser.add_argument("-t", "--target", type=bool, help="True if you want to only convert the target", default=False)
args = parser.parse_args()

# Loads the source and target map csvs
source_map_df = pandas.read_csv('data/source_map.csv', converters={'cuis':ast.literal_eval})
target_map_df = pandas.read_csv('data/target_map.csv', converters={'cuis':ast.literal_eval})

# Lioads the true positive/negative csvs if provided
if args.tp == '':
    tp_df = None
else:
    tp_df = pandas.read_csv(args.tp)

if args.tn == '':
    tn_df = None
else:
    tn_df = pandas.read_csv(args.tn)

# initialize mapping dicts
source_map = {}
target_map = {}

# build target mapping dict
for r in range(len(target_map_df)):
    for cui in target_map_df['cuis'][r]:
        if cui in target_map.keys():
            target_map[cui] += [target_map_df['id'][r]]
        else:
            target_map[cui] = [target_map_df['id'][r]]

# build source mapping dict if not specified to target only
if not args.target:
    for r in range(len(source_map_df)):
        for cui in source_map_df['cuis'][r]:
            if cui in source_map.keys():
                source_map[cui] += [source_map_df['id'][r]]
            else:
                source_map[cui] = [source_map_df['id'][r]]

def convert_df(df, source_map, target_map):
    """
    converts the target and source 

    :param df: The daraframe containing the sources and targets to be converted
    :param source_map: A dict containg the cuis as keys and curies as values
    :param target_map: A dict containg the cuis as keys and curies as values

    :return: A data frame with converted source and target ids
    """
    d = 0
    new_df_list = []
    count_flag = 'count' in df
    for row in range(len(df)):
        if df['source'][row] in source_map.keys() and df['target'][row] in target_map.keys():
            for src in source_map[df['source'][row]]:
                for trg in target_map[df['target'][row]]:
                    if count_flag:
                        new_df_list += [[df['count'][row],src,trg]]
                    else:
                        new_df_list += [[src,trg]]
        d += 1
        # This just prints out progress every 10% uncomment if you want this
        #if d % int(len(df)/10 + 1) == 0:
        #    print(d/len(df))

    if count_flag:
        new_df = pandas.DataFrame(new_df_list,columns = ['count','source','target'])
    else:
        new_df = pandas.DataFrame(new_df_list,columns = ['source','target'])
    return new_df

def convert_target(df,target_map):
    d = 0
    new_df_list = []
    count_flag = 'count' in df
    for row in range(len(df)):
        if df['target'][row] in target_map.keys():
            for trg in target_map[df['target'][row]]:
                if count_flag:
                    new_df_list += [[df['count'][row],df['source'][row],trg]]
                else:
                    new_df_list += [[df['source'][row],trg]]
        d += 1
        # This just prints out progress every 10% uncomment if you want this
        #if d % int(len(df)/10 + 1) == 0:
        #    print(d/len(df))

    if count_flag:
        new_df = pandas.DataFrame(new_df_list,columns = ['count','source','target'])
    else:
        new_df = pandas.DataFrame(new_df_list,columns = ['source','target'])
    return new_df

if tp_df is not None:
    if args.target:
        new_tp = convert_target(tp_df,target_map)
    else:
        new_tp = convert_df(tp_df,source_map,target_map)
    new_tp.to_csv(args.tp,index = False)

if tn_df is not None:
    if args.target:
        new_tn = convert_target(tn_df,target_map)
    else:
        new_tn = convert_df(tn_df,source_map,target_map)
    new_tn.to_csv(args.tn,index = False)




