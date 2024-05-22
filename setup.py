#!/usr/bin/env python
from os import path as op
from sys import version_info

from setuptools import setup, find_namespace_packages

from pyradio import version, __project__, __license__


def read(filename):
    ret = ''
    if op.exists(filename):
        with open(op.join(op.dirname(__file__), filename)) as f:
            ret = f.read()
    return ret

install_requires = []
if version_info < (2, 7):
    install_requires.append('argparse')

meta = dict(
    name=__project__,
    version=version,
    license=__license__,
    description=read('DESCRIPTION').rstrip(),
    platforms=('Any'),
    author='Ben Dowling',
    author_email='ben.m.dowling@gmail.com',
    url=' http://github.com/coderholic/pyradio',
    include_package_data=True,
    packages=find_namespace_packages(exclude=['devel', 'favicon']) + ['pyradio.__pycache__'],
    entry_points={
        'console_scripts': [
            'pyradio = pyradio.main:shell',
            'pyradio-client = pyradio.main:run_client'
        ]
    },
    install_requires=install_requires,
    test_suite = 'tests',
)


if __name__ == "__main__":
    setup(**meta)
