# -*- coding: utf-8 -*-

import asyncio
import pytest

from gitmesh.__main__ import main, _await
from unittest import mock


def test_main():
    with mock.patch('sys.argv', ['gitmesh', '--help']):
        with pytest.raises(SystemExit):
            main()


def test_await(event_loop):

    def hello(name):
        return 'Hello, %s!' % name

    async def hello_coroutine(name):
        return hello(name)

    def hello_future(name):
        f = asyncio.Future()
        f.set_result(hello(name))
        return f

    assert _await(event_loop, hello('world')) == 'Hello, world!'
    assert _await(event_loop, hello_coroutine('world')) == 'Hello, world!'
    assert _await(event_loop, hello_future('world')) == 'Hello, world!'
