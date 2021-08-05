#!/bin/bash

# output info used for dev
# The MD5 "/md5_sums_new/KG2.6.7/map_v1.0_KG2.6.7.txt.md5" is different from "/md5_sums_local/KG2.6.7/map_v1.0_KG2.6.7.txt.md5"

# team-expander-ops@sftp.transltr.io:/transltr-063208468694-sftp/team-expander/databases/KG2.6.7/map_v1.0_KG2.6.7.txt

# sftp -i /etc/ssh-key/ssh-key-SECRET_FILE -o StrictHostKeyChecking=no -pr team-expander-ops@sftp.transltr.io:/transltr-063208468694-sftp/team-expander/md5_sums/ /md5_sums_new

# sftp -i /etc/ssh-key/ssh-key-SECRET_FILE -o StrictHostKeyChecking=no -pr team-expander-ops@sftp.transltr.io:/transltr-063208468694-sftp/team-expander/databases/ /

# variables
sftp_url="team-expander-ops@sftp.transltr.io:/transltr-063208468694-sftp/team-expander"
databases_path="/databases"
md5_sums_new="/databases/md5_sums_new"
md5_sums_local="/databases/md5_sums_local"
currentDate=`date +"%Y-%m-%d %T"`

# welcome
echo "
      ################################################################################
      #                                                                              #
      #                                                                              #
      #                      ARAX Database Download Utility                          #
      #                                                                              #
      #                                                                              #
      ################################################################################"

# always get new md5 info
printf "Getting MD5 infor from sftp server...."
sftp -i /etc/ssh-key/ssh-key-SECRET_FILE -o StrictHostKeyChecking=no -pr ${sftp_url}/md5_sums/ $md5_sums_new
printf '\n'

# loop through MD5 infos 
for new_MD5 in $(find $md5_sums_new -type f); do 
    local_MD5=${new_MD5/$md5_sums_new/$md5_sums_local}
    # compare local MD5 with new MD5, if no local MD5 info available, cmp will return false. 
    # This handles the first time database download and in case new database file has been added. 
    if cmp -s "$new_MD5" "$local_MD5"; then
	       printf 'The MD5 "%s" is the same as "%s"\n\n' $new_MD5 $local_MD5
    else
         printf 'The MD5 "%s" is different from "%s"\n' $new_MD5 $local_MD5

         # build the current database file path. replace md5 directory with database directory
         temp=${new_MD5/$md5_sums_new/$databases_path}

         # absolute sftp server path of file to download
         file2download="$sftp_url${temp/.md5/}"
         file2download_localpath="${file2download/$sftp_url/}"
         # echo $file2download_localpath
         
         # if the file does not exist, create the directory and a dummy file, e.g. first time run or new database files added
         if ! [ -f "$file2download_localpath" ]; then
             install -D /dev/null ${file2download_localpath}
         fi

         # download the file
         printf 'Downloading from "%s" to "%s"...\n' "$file2download" "$file2download_localpath"
         sftp -i /etc/ssh-key/ssh-key-SECRET_FILE -o StrictHostKeyChecking=no -p $file2download $file2download_localpath
         printf '\n'
    fi
done

# rename new MD5 to local
printf 'renaming  "%s" to "%s"...\n' $md5_sums_new $md5_sums_local
mv $md5_sums_new $md5_sums_local
