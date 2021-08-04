#!/bin/bash
if kubectl -n rtx get secrets sftp-ssh-key; then
  echo "got hello secret"
else
  echo "no hello secret, creating now"
fi
