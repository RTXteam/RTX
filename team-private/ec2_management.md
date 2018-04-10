# Rtxdev EC2 Instance management guide

## Starting and Stoping the ec2 instance

To start or stop an ec2 instace do the following:
* follow this [link](http://ec2startstop.saramsey.org/cgi-bin/manage-instances-cgi.py)
* enter the username and password when propted
* look to see that the ec2 instance is not already in the state you want it to be in
* check the bubble next to the instance you wish to alter the state of
* check start (or stop) instance
* enter the instance specific passcode
* click on the submit button

**NOTE:** I don't think it wise to post the passwords or username here on github. If you do not have any of there feel free to email me (Finn) or message me on the isb-ncats slack channel to ask for them.


## Open Ports on rtxdev ec2 instance

|port | used for|
|----|------|
|:7474| rtxdev neo4j container HTTP access|
|:7473| rtxdev neo4j container HTTPS access|
|:7687| rtxdev neo4j container BOLT access|
|:7674| rtxsteve neo4j container HTTP access|
|:7673| rtxsteve neo4j container HTTPS access|
|:7887| rtxsteve neo4j container BOLT access|
|:3306| SemMedDB mySQL container|
|:3406| UMLS nySQL container|
