FROM alpine
RUN apk update && apk add --no-cache openssh bash jq zsh 
RUN mkdir -p /etc/ssh-key
RUN mkdir /databases
COPY ./download_database.sh /
CMD /bin/bash
