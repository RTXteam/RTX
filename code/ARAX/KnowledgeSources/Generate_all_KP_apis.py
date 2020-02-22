import sys
import os
import importlib

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/")
mypath = os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/"
onlyfiles = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
not_parsed = 0
parsed = 0
fid = open('API_LIST.yaml', 'w')
fid.write("""# Example list of KP API's ARAX has the ability to automatically utilize
# Each API provider should add one entry under APIs
# NOTE: THIS IS A VERY INCOMPLETE LIST OF ALL THE KP'S ARAX/RTX IS USING ONLY FOR KG1 (eg. only 12 of 28+ are listed here)
# "metadata" points to the API's openapi metadata
#            a relative path in this repo, or a full URL
# "translator" is a placeholder for translator specific attributes
# "parser" is a relative path indicating where the ARAX parser resides
# "name" is the name of the knowledge provider or source (mainly for internal use or human discussion)
# "functionalities" is a dictionary of endpoint functionality that this KP can provide
APIs:\n""")
for file in onlyfiles:
    if file[0:5] == "Query":
        try:
            module_name = file.split('.')[0]
            m = importlib.import_module(file.split('.')[0])
            metadata = getattr(m, module_name)().API_BASE_URL
            functionalities = getattr(m, module_name)().HANDLER_MAP
            fid.write(f"""  - name: {module_name[5:]}\n""")
            fid.write(f"""    translator:\n          - returnjson: true\n          - metadata: {metadata}\n""")
            fid.write("""    ARAXInfo:\n""")
            fid.write(f"""          - parser: ../../reasoningtool/kg-construction/{module_name}.py\n""")
            fid.write(f"""          - functionalities: {functionalities}\n""")
            fid.write(f"""          - name: {module_name[5:]}\n\n""")
            parsed += 1
        except:
            not_parsed += 1
#print(not_parsed)
#print(parsed)
fid.close()


#import QueryBioLink
#q = QueryBioLink.QueryBioLink()
#print(q.API_BASE_URL)
#print(q.HANDLER_MAP)