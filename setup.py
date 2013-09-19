#!/usr/bin/env python
from os import path as op
from sys import version_info

from setuptools import setup, find_packages

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
    description=read('DESCRIPTION'),
    long_description=read('README.md'),
    platforms=('Any'),
    author='Ben Dowling',
    author_email='ben.m.dowling@gmail.com',
    url=' http://github.com/coderholic/pyradio',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'pyradio = pyradio.main:shell',
        ]
    },
    install_requires=install_requires,
    test_suite = 'tests',
)


if __name__ == "__main__":
    setup(**meta)
