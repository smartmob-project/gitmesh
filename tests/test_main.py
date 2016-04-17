# -*- coding: utf-8 -*-

import pytest

from gitmesh.__main__ import main
from unittest import mock


def test_main():
    with mock.patch('sys.argv', ['gitmesh', '--help']):
        with pytest.raises(SystemExit):
            main()
