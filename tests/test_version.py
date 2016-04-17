# -*- coding: utf-8 -*-


import gitmesh
import six


def test_version_string():
    assert isinstance(gitmesh.version, six.text_type)
