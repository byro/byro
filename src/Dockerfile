FROM python:3.8-slim as common-base
MAINTAINER byro team

ARG PLUGINS=""

ENV DEBIAN_FRONTEND noninteractive
ENV DJANGO_SETTINGS_MODULE byro.settings
ENV BYRO_CONFIG_FILE /byro/config/byro.cfg

RUN useradd uid1000 -d /home/uid1000 && \
    mkdir -p /home/uid1000 && \
    chown uid1000: /home/uid1000 && \
    mkdir -p /byro /byro/data /byro/data/media /byro/data/logs && \
    chown -R uid1000: /byro


FROM common-base as base-builder
RUN mkdir -p /app
RUN pip install -U pip setuptools
WORKDIR /app

# Stage 1: Extract dependency information from setup.py alone
#  Allows docker caching until setup.py changes
FROM base-builder as dependencies

COPY setup.py .
COPY byro/__init__.py ./byro/__init__.py
RUN python setup.py egg_info

# Stage 2: Install dependencies based on the information extracted from the previous step
#  Caveat: Expects an empty line between base dependencies and extras, doesn't install extras
FROM base-builder as builder
RUN apt-get update && \
    apt-get install -y zsh gettext libjpeg-dev libmagic-dev build-essential python3-dev
RUN mkdir -p /install
COPY --from=dependencies /app/byro.egg-info/requires.txt /tmp/
RUN sh -c 'pip install --no-warn-script-location --prefix=/install $(grep -e ^$ -m 1 -B 9999 /tmp/requires.txt) gunicorn psycopg2-binary'


ADD . /app

# Stage 3: Install application (no-deps, since we already have the dependencies)
RUN sh -c 'pip install --no-warn-script-location --prefix=/install --no-deps .'


# FIXME Add plugins here


# Stage 4: Install application into this temporary container, in order to have both source and compiled files
#  Compile assets from source
RUN cp -r /install/* /usr/local
ADD byro.docker.cfg /byro/config/byro.cfg
RUN sh -c 'python manage.py collectstatic --no-input && python manage.py compress && python manage.py collectstatic --no-input'


# Stage 5: Install compiled static assets, support files, apache, and postgresql into clean image
FROM common-base

RUN apt-get update && \
    apt-get install -y libmagic1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/static.dist /app/static.dist
COPY --from=builder /install /usr/local
ADD byro.docker.cfg /byro/config/byro.cfg
ADD docker-entrypoint.sh /docker-entrypoint.sh

WORKDIR /byro
EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["byro"]
