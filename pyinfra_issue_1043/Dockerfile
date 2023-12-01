FROM ubuntu:18.04
RUN apt-get update && \
      apt-get -y install sudo
RUN useradd -m peter && echo "peter:peter" | chpasswd && adduser peter sudo
USER peter
CMD /bin/bash
