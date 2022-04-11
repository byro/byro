ARG language=C
ARG PYTHON_VERSION=3.10.4
ARG BYRO_USER=byro
ARG BYRO_UID=23000
ARG DEVELOPMENT=0

FROM python:${PYTHON_VERSION}-slim as common-base
MAINTAINER byro team

ENV DEBIAN_FRONTEND noninteractive
ENV DJANGO_SETTINGS_MODULE byro.settings
ENV BYRO_CONFIG_FILE /byro/config/byro.cfg
ENV PYTHONUNBUFFERED 0

ARG language
ARG BYRO_USER
ARG BYRO_UID
ARG DEVELOPMENT

ENV LANG $language
ENV BYRO_USER "$BYRO_USER"
ENV BYRO_UID "$BYRO_UID"
ENV DEVELOPMENT "${DEVELOPMENT}"

RUN groupadd --gid "${BYRO_UID}" "${BYRO_USER}" && \
    useradd --uid "${BYRO_UID}" --gid "${BYRO_UID}" ${BYRO_USER} -d /home/${BYRO_USER} && \
    mkdir -p /home/${BYRO_USER} && \
    chown ${BYRO_USER}:${BYRO_USER} /home/${BYRO_USER} && \
    mkdir -p /byro /byro/data /byro/data/media /byro/data/logs /byro/data/misc && \
    chown -R ${BYRO_USER}:${BYRO_USER} /byro


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
ENV PYTHONPATH /install:/app

# Stage 3: Install application (no-deps, since we already have the dependencies),
RUN pip install --no-warn-script-location --prefix=/install --no-deps .

ARG INSTALL_PLUGINS
ENV PLUGINS "$INSTALL_PLUGINS"

RUN test -z "$PLUGINS" || (echo Installing $PLUGINS; pip install --no-warn-script-location --prefix=/install $PLUGINS && cp -r /install/* /usr/local/ )


# Stage 4: Compile assets from source
RUN chown -R "${BYRO_USER}:${BYRO_USER}" /byro /app && \
    su -p ${BYRO_USER} -c "python manage.py compilemessages" && \
    su -p ${BYRO_USER} -c "python manage.py collectstatic --no-input" && \
    su -p ${BYRO_USER} -c "python manage.py compress" && \
    su -p ${BYRO_USER} -c "python manage.py collectstatic --no-input"


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
VOLUME ["/byro/config", "/byro/data/misc", "/byro/data/media", "/byro/data/logs"]
CMD ["byro"]
