# -*- coding: utf-8 -*-

from setuptools import (
    find_packages,
    setup,
)

def readfile(path):
    with open(path, 'r') as stream:
        content = stream.read()
        if hasattr(path, 'decode'):
            content = content.decode('utf-8')
        return content

version = readfile('gitmesh/version.txt').strip()
readme = readfile('README.rst')

setup(
    name='gitmesh',
    version=version,
    url='https://github.com/smartmob-project/gitmesh',
    maintainer='Andre Caron',
    maintainer_email='ac@smartmob.org',
    description='Tools for building a Git server',
    long_description=readme,
    packages=find_packages(),
    package_data={
        'gitmesh': [
            'version.txt',
        ],
    },
    scripts=[
        'bin/pre-receive',
        'bin/update',
        'bin/post-receive',
        'bin/post-update',
    ],
    entry_points={
        'console_scripts': [
            'gitmesh = gitmesh.__main__:main',
        ],
        'gitmesh.pre_receive': [],
        'gitmesh.update': [],
        'gitmesh.post_receive': [],
        'gitmesh.post_update': [],
    },
    install_requires=[
        'click>=6.6',
    ],
)
