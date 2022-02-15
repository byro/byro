from codecs import open
from distutils.command.build import build
from os import environ, path

from setuptools import find_packages, setup

from byro import __version__ as byro_version

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
try:
    with open(path.join(here, "../README.rst"), encoding="utf-8") as f:
        long_description = f.read()
except:  # noqa
    long_description = ""


class CustomBuild(build):
    def run(self):
        environ.setdefault("DJANGO_SETTINGS_MODULE", "byro.settings")
        try:
            import django
        except ModuleNotFoundError:
            return
        django.setup()
        from django.conf import settings
        from django.core import management

        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_OFFLINE = True

        management.call_command("compilemessages", verbosity=1)
        management.call_command("collectstatic", verbosity=1, interactive=False)
        management.call_command("compress", verbosity=1)
        build.run(self)


cmdclass = {"build": CustomBuild}


setup(
    name="byro",
    version=byro_version,
    license="Apache License 2.0",
    python_requires=">=3.8",
    description="Membership and fees management for associations, clubs and groups",
    long_description=long_description,
    url="https://byro.cloud",
    author="Tobias Kunze",
    author_email="r@rixx.de",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Intended Audience :: Developers",
        "Intended Audience :: Other Audience",
        "License :: OSI Approved",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    keywords="members membership fees club group clubs associations association",
    install_requires=[
        "canonicaljson==1.5.0",  # https://github.com/matrix-org/python-canonicaljson/blob/master/CHANGES.md
        "chardet>=4.0,<4.1",  # https://github.com/chardet/chardet/releases
        "celery>=5.1,<6.0",  # search for "what's new" on http://docs.celeryproject.org/en/latest/
        "csscompressor~=0.9.5",  # 2017-11, no changelog, https://github.com/sprymix/csscompressor
        "dateparser>=1.1,<1.2",  # https://github.com/scrapinghub/dateparser/blob/master/HISTORY.rst
        "Django>=3.2,<3.3",  # https://docs.djangoproject.com/en/2.0/releases/
        "django-annoying~=0.10.0",  # https://github.com/skorokithakis/django-annoying/releases
        "django-bootstrap4>=3.0,<3.1",  # http://django-bootstrap4.readthedocs.io/en/latest/history.html
        "django-compressor~=2.4",  # https://django-compressor.readthedocs.io/en/latest/changelog/
        "django-extensions>=3.1,<3.2",  # https://github.com/django-extensions/django-extensions/blob/master/CHANGELOG.md
        "django-formset-js-improved==0.5.0.2",  # no changelog, https://github.com/pretix/django-formset-js
        "django-i18nfield>=1.9,<1.10",  # 2017-11, no changelog, https://github.com/raphaelm/django-i18nfield/
        "django-libsass>=0.8,<0.10",  # inactive, https://github.com/torchbox/django-libsass/blob/master/CHANGELOG.txt
        "django-localflavor>=3.0,<3.2",
        "django-select2>=7.7,<7.11",  # https://github.com/applegrew/django-select2/releases
        "django-solo>=1.2.0,<2.1",  # https://github.com/lazybird/django-solo/blob/master/CHANGES
        "inlinestyler~=0.2",  # https://github.com/dlanger/inlinestyler/blob/master/CHANGELOG
        "jinja2>=2.10.1",  # https://github.com/pallets/jinja/blob/master/CHANGES.rst
        "psycopg2-binary",
        "python-dateutil",
        "python-magic~=0.4.0",
        "pynacl>=1.4,<1.6",  # https://github.com/pyca/pynacl/blob/master/CHANGELOG.rst
        "qrcode[pil]>=7.3,<7.4",  # https://github.com/lincolnloop/python-qrcode/blob/master/CHANGES.rst
        "unicodecsv~=0.14.0",
        "more-itertools>=8.10,<8.13",
        "schwifty==2022.2.0",
    ],
    extras_require={
        "dev": [
            "black",
            "check-manifest",
            "docformatter",
            "flake8",
            "flake8-bugbear",
            "freezegun",
            "isort",
            "ipython",
            "pytest",
            "pytest-cov",
            "pytest-django",
            "pytest-sugar",
        ],
        "mysql": ["mysqlclient"],
        "postgres": ["psycopg2-binary"],
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    zip_safe=False,
    cmdclass=cmdclass,
)
