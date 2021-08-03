FROM centos:7
RUN yum update -y
RUN yum install epel-release -y
RUN curl -sL https://rpm.nodesource.com/setup_12.x | bash -
RUN yum install nodejs -y
RUN yum install git -y
RUN npm install -g @angular/cli

WORKDIR /root
# do we need to git clone again?
RUN git clone https://github.com/couchbaselabs/eagle-eye.git
WORKDIR eagle-eye
RUN git checkout origin/ee-v2
WORKDIR ./webapp

RUN npm install
EXPOSE 4200
CMD ng serve --host 0.0.0.0 --configuration production