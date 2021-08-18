FROM centos:7
RUN yum update -y
RUN yum install -y python3
RUN yum install git wget make gcc bzip2 zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel readline-devel sqlite sqlite-devel libffi-devel gcc-c++ python-devel python-pip -y
RUN yum install -y sendmail sendmail-cf m4     && hostname >> /etc/mail/relay-domains     && m4 /etc/mail/sendmail.mc > /etc/mail/sendmail.cf
RUN sed -i -e "s/Port=smtp,Addr=127.0.0.1, Name=MTA/Port=smtp, Name=MTA/g"     /etc/mail/sendmail.mc
WORKDIR /root
RUN wget https://www.python.org/ftp/python/3.9.5/Python-3.9.5.tgz
RUN tar -xvf Python-3.9.5.tgz
WORKDIR Python-3.9.5
RUN ./configure --enable-optimizations
RUN make altinstall
RUN alternatives --install /usr/local/bin/python3 python3 /usr/local/bin/python3.9 1
RUN alternatives --install /usr/local/bin/pip3 pip3 /usr/local/bin/pip3.9 1
WORKDIR /root
# clone the repo
RUN git clone https://github.com/couchbaselabs/eagle-eye.git
WORKDIR eagle-eye
RUN git checkout origin/ee-v2
RUN mkdir server/server_logs
# install dependencies in the virtual env
RUN pip3 install Flask
RUN pip3 install flask-restful
RUN pip3 install flask-cors
RUN pip3 install paramiko
RUN pip3 install httplib2
RUN pip3 install requests
RUN pip3 install pytz
# install couchbase python sdk
RUN python3 -m pip install --upgrade pip setuptools wheel
RUN yum install -y gcc gcc-c++ python3-devel python3-pip cmake
RUN pip3 install couchbase
CMD ["./start-server.sh"]