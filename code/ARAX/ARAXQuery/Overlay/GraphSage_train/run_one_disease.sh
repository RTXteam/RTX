num=$2
batch=$1

python /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/scripts/calculate_probabilities_in_one_disease.py --embfile /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/data/disease_drug_only.txt --drugfile /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/data/drug_ids.txt --diseasefile /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/data/diseases/batch${batch}/curie${num} --modelfile /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/data/LogModel.pkl --outpath /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/results

echo 'complete' >> /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/run/temp_record.log
