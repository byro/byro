FROM python:3.6
MAINTAINER byro team

EXPOSE 8020

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y zsh

# user
RUN useradd uid1000 -d /home/uid1000
RUN mkdir -p /home/uid1000 && chown uid1000: /home/uid1000
VOLUME /home/uid1000
RUN chown -R uid1000: /opt

ADD requirements.txt /opt/code/requirements.txt
ADD requirements/production.txt /opt/code/requirements/production.txt
ADD requirements/development.txt /opt/code/requirements/development.txt
WORKDIR /opt/code
RUN pip install -Ur requirements.txt
RUN pip install -Ur requirements/development.txt
ADD install_local_plugins.sh /opt/code/install_local_plugins.sh
ADD . /opt/code

RUN /bin/zsh install_local_plugins.sh

WORKDIR /opt/code

# used for production. on dev set by docker-compose
# will be fixed later
#ENTRYPOINT ["./start.sh"]
#CMD ["web"]
