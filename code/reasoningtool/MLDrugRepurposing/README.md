# Make sure python is set up correctly

make sure you have python3 installed and that the contents of [Requirements.txt](https://github.com/RTXteam/RTX/blob/master/requirements.txt) are installed

# Download the SemMedDB MySQL dump

Download can be found here: https://skr3.nlm.nih.gov/SemMedDB/download/download.html

Download the PREDICATION table from the above link and place it into the data directory.

# Edit the MLDR.sh file variables

There are several variables at the top of the MLDR.sh bash script. They are seperated into groups and have decriptions of what they do written above them. You will need to edit some of these (like neo4j log in credentials and url:port) to fit your local system before running MLDR.sh 

# Make predictions using predictor.py

If you want to make predictions on a data set format it in a csv with the headers source and target using curie ids (CHEMBL for drugs and DOID/OMIM/HP) as identifiers formatted as such:

source |	target
----- | ----
ChEMBL:1622 |	DOID:399
ChEMBL:730 |	OMIM:613658
ChEMBL:1484 |	OMIM:601367
ChEMBL:1237022 |	DOID:0060407
ChEMBL:504 |	DOID:0050275
ChEMBL:714 |	DOID:9675
ChEMBL:504 |	DOID:0050638
ChEMBL:1909300 | HP:0000421

Then if you wish to make a prediction at the same time simply uncomment the predictor.py commands at the end of MLDR.sh and it do it all in one run. Otherwise, you can simply follow the skeleton of the command and just run it in the termainal after MLDR.sh has generated the model. 

