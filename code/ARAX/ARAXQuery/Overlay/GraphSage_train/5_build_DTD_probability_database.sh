## create a folder for storing the input data and output results for this database
mkdir ~/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp
cd ~/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp
## generate a few folders
mkdir data results run
cd ~/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/data
cp ~/RTX/code/ARAX/ARAXQuery/Overlay/predictor/retrain_data/LogModel.pkl .
cat ~/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/kg2canonicalized_data/drugs_in_graph.txt | cut -f 1 > drug_ids.txt
cat ~/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/kg2canonicalized_data/diseases_in_graph.txt | cut -f 1 | sed '1d' > disease_ids.txt
scp rtxconfig@arax.ncats.io:/data/orangeboard/databases/KG2.3.4/map_v1.0.txt map.txt
scp rtxconfig@arax.ncats.io:/data/orangeboard/databases/KG2.3.4/rel_max_v1.0.emb.gz rel_max.emb.gz
python ~/RTX/code/ARAX/ARAXQuery/Overlay/GraphSage_train/py_scripts/py_scripts/prepare_data_for_DTD_prob_database.py
mkdir diseases
cd ~/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/data/diseases
split -l 38 -a 4 -d ./disease_ids.txt batchfile
for i in {0000..7333}; do mkdir batch$i;done
for i in {0000..7333}; do mv batchfile$i batch$i;done
for i in {0000..7333}; do mv ~/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/data/diseases/batch$i; split -l 1 -a 2 -d batchfile$i curie;done
cp ~/RTX/code/ARAX/ARAXQuery/Overlay/GraphSage_train/run_one_disease.sh ../../run/
cp ~/RTX/code/ARAX/ARAXQuery/Overlay/GraphSage_train/run.sh ../../run/
