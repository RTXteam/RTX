#!/bin/bash

# output info used for dev
# The MD5 "/md5_sums_new/KG2.6.7/map_v1.0_KG2.6.7.txt.md5" is different from "/md5_sums_local/KG2.6.7/map_v1.0_KG2.6.7.txt.md5"

# team-expander-ops@sftp.transltr.io:/transltr-063208468694-sftp/team-expander/databases/KG2.6.7/map_v1.0_KG2.6.7.txt

# sftp -i /etc/ssh-key/ssh-key-SECRET_FILE -o StrictHostKeyChecking=no -pr team-expander-ops@sftp.transltr.io:/transltr-063208468694-sftp/team-expander/md5_sums/ /md5_sums_new

# sftp -i /etc/ssh-key/ssh-key-SECRET_FILE -o StrictHostKeyChecking=no -pr team-expander-ops@sftp.transltr.io:/transltr-063208468694-sftp/team-expander/databases/ /

# variables
config_file="/configs/configv2.json"
# associative array serves as dict
# here we build db_arr with db_path_pvc as its key and 1 as its value, which equivilent to "set"
# db_arr:     most updated db file path on PVC (in this case, /databases)
# db_MD5_arr: most updated MD5 file path of elements in db_arr
declare -A db_arr new_db_MD5_arr
db_folder="/databases"
sftp_url="team-expander-ops@sftp.transltr.io:/transltr-063208468694-sftp/team-expander"
sftp_key="/etc/ssh-key/team-expander-ops-sshkey-secret"
md5_sums_new="/databases/md5_sums_new"
md5_sums_local="/databases/md5_sums_local"

# welcome
echo "
      ################################################################################
      #                                                                              #
      #                                                                              #
      #                      KG2 Database Download Utility                           #
      #                                                                              #
      #                                                                              #
      ################################################################################"

# build db_arr which includes all needed db files in configv2.json
echo "Reading ${confgi_file} and building new db_arr specified in ${config_file}....."
printf "\n"
for db in $(jq -r '.Contextual.Production | keys | .[]' ${config_file})
do
  # NOTE: if there's no .path value, the result will be a string "null"
  db_path=$(jq -r '.Contextual.Production.'${db}' | .path' ${config_file})
  if [ ${db_path} != "null" ]
  then
    db_path_pvc="${db_path/'/translator/data/orangeboard'}"
    # echo $db_path_pvc
    db_arr[${db_path_pvc}]=1
    new_db_MD5="${db_path/'/translator/data/orangeboard/databases'/${md5_sums_new}}.md5"
    new_db_MD5_arr[${new_db_MD5}]=1
  fi
done

# echo "${!db_arr[@]}"
# echo "${!new_db_MD5_arr[@]}"


# clean up current db first
# check if there's db file not listed in configv2.json and rm 
# this is useful when a new db (or a new version of existing db) rolls out
# and we only want to keep what is specificed in configv2.json file
echo "Removing outdated db files......"
for existing_db in $(find $db_folder -type f)
do 
  # check if filename ends with .md5, which is NOT db file
  if [[ ! "${existing_db}" == *.md5 ]]
  then
    # check if existing_db in db_arr, if not, rm it
    if [[ ! ${db_arr[${existing_db}]} ]]
    then
      echo "${existing_db} is NOT in db_arr, rm it!"
      # NOTE: commented out for debugging since redownloading takes too long
      # PLEASE UNCOMMENT BELOW TO ENABLE DB CLEANUP FEATURE
      # rm ${existing_db}
    fi
  fi
done
printf "\n"

# always get new md5 info
echo "Getting MD5 info from sftp server...."
sftp -i $sftp_key -o StrictHostKeyChecking=no -pr ${sftp_url}/md5_sums/ $md5_sums_new
printf '\n'

# this is tricky, we download all MD5 info, some are needed, some are not
# we need to loop through all downloaded MD5s, remove others but only keep the needed ones, which is from the configv2.json
for MD5 in $(find $md5_sums_new -type f)
do
  if [[ ! ${new_db_MD5_arr[${MD5}]} ]]
  then
    rm ${MD5}
  fi
done


# loop through new_db_MD5_arr
for new_MD5 in "${!new_db_MD5_arr[@]}" 
do 
    local_MD5=${new_MD5/$md5_sums_new/$md5_sums_local}
    # compare local MD5 with new MD5, if no local MD5 info available, cmp will return false. 
    # This handles the first time database download and in case new database file has been added. 
    if cmp -s "$new_MD5" "$local_MD5"
    then
       printf 'The MD5 "%s" is the same as "%s"\n\n' $new_MD5 $local_MD5
    else
      # check if local_MD5 exists, if not, that's also a new db file to download
      if [ ! -f "$local_MD5" ]
      then
        printf 'The MD5 "%s" does NOT exist. This is a newly-added db...\n' $local_MD5
      else
        printf 'The MD5 "%s" is different from "%s"\n' $new_MD5 $local_MD5
      fi
      # build the current database file path. replace md5 directory with database directory
      temp=${new_MD5/$md5_sums_new/$db_folder}
      # absolute sftp server path of file to download
      file2download="$sftp_url${temp/.md5/}"
      file2download_localpath="${file2download/$sftp_url/}"
      # echo $file2download_localpath
      # if the file does not exist, create the directory and a dummy file, e.g. first time run or new database files added
      if ! [ -f "$file2download_localpath" ]
      then
          install -D /dev/null ${file2download_localpath}
      fi
      # download the file
      printf 'Downloading from "%s" to "%s"...\n' "$file2download" "$file2download_localpath"
      sftp -i $sftp_key -o StrictHostKeyChecking=no -p $file2download $file2download_localpath
      printf '\n'
    fi
done

# rename new MD5 to local
printf 'renaming  "%s" to "%s"...\n' $md5_sums_new $md5_sums_local
rm -rf $md5_sums_local
mv $md5_sums_new $md5_sums_local
