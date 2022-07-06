#!/bin/bash

# variables 
projectName="arax"
namespace="rtx"
# replace place_holder with values from env var
# env var's key needs to be the same as the place_holder
toReplace=('BUILD_VERSION')

# export .env values to env vars
# export $(egrep -v '^#' .env)

# printenv

# replace variables in values.yaml with env vars

for item in "${toReplace[@]}";
do
  sed -i.bak \
      -e "s/${item}/${!item}/g" \
      values.yaml
  rm values.yaml.bak
done

# deploy helm chart
helm -n ${namespace} upgrade --install ${projectName} -f arax.values.ncats.yaml ./
