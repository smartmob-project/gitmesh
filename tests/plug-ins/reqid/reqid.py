# -*- coding: utf-8 -*-


import os


def pre_receive(updates):
    print('request ID: "%s".' % (
        os.environ.get('GITMESH_REQUEST_ID', '?'),
    ))
