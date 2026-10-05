import sys
from importlib import reload
import json
import ast
sys.path.append('/home/dkoslicki/Dropbox/Repositories/RTX/code/reasoningtool')
sys.path.append('/home/dkoslicki/Dropbox/Repositories/RTX/code/reasoningtool/QuestionAnswering')
sys.path.append('/home/dkoslicki/Dropbox/Repositories/RTX/code/reasoningtool/kg-construction')
sys.path.append('/home/dkoslicki/Dropbox/Repositories/RTX/code/')
import KGNodeIndex
k = KGNodeIndex.KGNodeIndex()
k.connect()
#k.createDatabase()
#k.createNodeTable()
import ReasoningUtilities as RU
import WF5
WF5 = WF5.WF5()

question_graph = json.loads('{"question_graph":{"nodes":[{"id":"n0","type":"chemical_substance","set":false,"name":"Albuterol","curie":["CHEMBL.COMPOUND:CHEMBL714"]},{"id":"n1","type":"protein"},{"id":"n2","type":"phenotypic_feature"}],"edges":[{"id":"e0","source_id":"n0","target_id":"n1","type":"physically_interacts_with"},{"id":"e1","source_id":"n1","target_id":"n2","type":"has_phenotype"}]}}')

fid = open('WF5chemical_substances.txt', 'r')
for chemical_name in fid.readlines():
	chemical_name = chemical_name.strip()
	curies = k.get_curies(chemical_name)
	print(curies)
	if curies:
		for curie in curies:
			if RU.get_node_property(curie, "label") == "chemical_substance":
				res = WF5.answer(curie, "phenotypic_feature", ["physically_interacts_with","has_phenotype"], use_json=True, directed=False)
				res_dict = res.response.to_dict()
				res_dict['question_graph'] = question_graph['question_graph']
				response = res.response.from_dict(res_dict)

				if res:
					with open("WF5results/%s_WF5_results.json" % chemical_name, 'w') as fid:
						fid.write("%s" % json.dumps(res_dict, sort_keys=True, indent=2))

				break


