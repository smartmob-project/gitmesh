# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='echo',
    version='0.1.0',
    py_modules=['echo'],
    entry_points={
        'gitmesh.pre_receive': [
            'echo = echo:pre_receive',
        ],
        'gitmesh.update': [
            'echo = echo:update',
        ],
        'gitmesh.post_receive': [
            'echo = echo:post_receive',
        ],
    },
)
