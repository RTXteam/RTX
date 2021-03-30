for i in {4903..7332} #7333 4903..7332
do
	echo 'Running batch'${i}
	touch /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/run/temp_record.log 
	for j in {00..37}
	do
			sh /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/run/run_one_disease.sh $i $j &
	done
	check=$(wc -l /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/run/temp_record.log  | cut -d" " -f 1)
	while [ "$check" -ne "38" ]
	do
			sleep 5
			check=$(wc -l /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/run/temp_record.log  | cut -d" " -f 1)
	done
	echo "Finsh batch"${i}
	rm /home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/temp/run/temp_record.log
done

