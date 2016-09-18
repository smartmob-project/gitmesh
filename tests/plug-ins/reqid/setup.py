# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='reqid',
    version='0.1.0',
    py_modules=['reqid'],
    entry_points={
        'gitmesh.pre_receive': [
            'reqid = reqid:pre_receive',
        ],
    },
)
