FROM python:3.9-slim as common-base
MAINTAINER byro team

ARG language=C
ARG INSTALL_PLUGINS

ENV DEBIAN_FRONTEND noninteractive
ENV DJANGO_SETTINGS_MODULE byro.settings
ENV BYRO_CONFIG_FILE /byro/config/byro.cfg
ENV LANG $language
ENV PLUGINS "$INSTALL_PLUGINS"

RUN useradd uid1000 -d /home/uid1000 && \
    mkdir -p /home/uid1000 && \
    chown uid1000: /home/uid1000 && \
    mkdir -p /byro /byro/data /byro/data/media /byro/data/logs /byro/data/misc && \
    chown -R uid1000: /byro


FROM common-base as base-builder
RUN mkdir -p /app
RUN pip install -U pip setuptools
WORKDIR /app

# Stage 1: Extract dependency information from setup.py alone
#  Allows docker caching until setup.py changes
FROM base-builder as dependencies

COPY ./setup.py .
COPY ./byro/__init__.py ./byro/__init__.py
RUN python setup.py egg_info

# Stage 2: Install dependencies based on the information extracted from the previous step
#  Caveat: Expects an empty line between base dependencies and extras, doesn't install extras
#  Also copies all installed packages to /usr/local for subsequent commands to find
FROM base-builder as builder
RUN apt-get update && \
    apt-get install -y zsh gettext libjpeg-dev libmagic-dev build-essential python3-dev git
RUN mkdir -p /install
COPY --from=dependencies /app/byro.egg-info/requires.txt /tmp/
RUN sh -c 'pip install --no-warn-script-location --prefix=/install $(grep -e ^$ -m 1 -B 9999 /tmp/requires.txt) gunicorn psycopg2-binary && cp -r /install/* /usr/local/'


ADD . /app
ADD ./byro.docker.cfg /byro/config/byro.cfg
ENV PYTHONPATH /install:/plugin_install:/app

# Stage 3: Install application (no-deps, since we already have the dependencies),
RUN pip install --no-warn-script-location --prefix=/install --no-deps .

RUN test -z "$PLUGINS" || (echo Installing $PLUGINS; pip install --no-warn-script-location --prefix=/install $PLUGINS && cp -r /install/* /usr/local/ )


# Stage 4: Compile assets from source
RUN python manage.py compilemessages && \
    python manage.py collectstatic --no-input && \
    python manage.py compress && \
    python manage.py collectstatic --no-input


# Stage 5: Install compiled static assets, support files, apache, and postgresql into clean image
FROM common-base

# FIXME The locale logic is probably broken for the "C" case, and hard to debug
RUN apt-get update && \
    apt-get install -y libmagic1 locales && \
    bash -c "(grep \"^${LANG} \" /usr/share/i18n/SUPPORTED | head -n 1 > /etc/locale.gen && /usr/sbin/locale-gen) || rm /etc/locale.gen" && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/static.dist /app/static.dist
COPY --from=builder /install /usr/local
COPY --from=builder /byro/config/byro.cfg /byro/config/byro.cfg
ADD ./docker-entrypoint.sh /docker-entrypoint.sh

WORKDIR /byro
EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["byro"]
