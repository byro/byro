FROM python:3.6
MAINTAINER byro team

EXPOSE 8020

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y zsh gettext libjpeg-dev libmagic-dev

RUN useradd uid1000 -d /home/uid1000
RUN mkdir -p /home/uid1000 && chown uid1000: /home/uid1000
RUN mkdir -p /byro && chown uid1000: /byro

ADD . /byro
ADD byro.docker.cfg /byro/byro.cfg
RUN cd /byro && pip3 install -e .
RUN cd /byro && /bin/zsh install_local_plugins.sh

CMD ["/bin/bash"]

WORKDIR /byro
ENTRYPOINT ["python3","manage.py","runserver"]
