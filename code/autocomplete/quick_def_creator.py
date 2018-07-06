import json

def get_data_for_json(source):
    data = {}

    # read data for instant definitions here
    # either from source (knowledge graph, db, etc) or somewhere else
    # all keys should be lower case
    # definition can contain html for formatting
    
    #dummy data for testing
    data["lovastatin"] = "<strong>Lovastatin</strong> is a statin drug, used for lowering cholesterol in those with hypercholesterolemia to reduce risk of cardiovascular disease."
    data["hemoglobin"] = "<strong>Hemoglobin</strong> or haemoglobin, abbreviated Hb or Hgb, is the iron-containing oxygen-transport metalloprotein in the red blood cells of all vertebrates (with the exception of the fish family Channichthyidae) as well as the tissues of some invertebrates."
    data["cancer"] = "<strong>Cancer</strong> is a group of diseases involving abnormal cell growth with the potential to invade or spread to other parts of the body."

    return data

def write_data_to_json(data):
    with open('./data/quick_def.json','w') as output:
        output.write("var quick_def = ")
        output.write(json.dumps(data))

data = get_data_for_json(None)
write_data_to_json(data)
