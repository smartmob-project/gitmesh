# -*- coding: utf-8 -*-


import aiohttp
import asyncio
import click.testing
# import logging
import pytest
import testfixtures

from gitmesh import __main__
from gitmesh.storage import Storage, check_output
from gitmesh.server import serve_until


def merge_envs(lhs, rhs):
    env = {}
    env.update(lhs)
    env.update(rhs)
    return env


@pytest.fixture
def run():
    async def run(*args, **kwds):
        return await check_output(*args, **kwds)
    return run


@pytest.yield_fixture(scope='function')
def storage():
    with testfixtures.TempDirectory(create=True) as directory:
        yield Storage(directory.path)
        directory.cleanup()


@pytest.yield_fixture(scope='function')
def workspace():
    with testfixtures.TempDirectory(create=True) as directory:
        yield Storage(directory.path)
        directory.cleanup()


@pytest.fixture
def cli():
    # See: http://click.pocoo.org/5/testing/
    def run(command, input=None):
        print('RUN:', command)
        runner = click.testing.CliRunner()
        result = runner.invoke(
            __main__.cli, command,
            obj={},
            env={},
            input=input,
        )
        if result.exception:
            print(result.exc_info)
            raise result.exception
        return result.output.strip()
    return run


@pytest.yield_fixture(scope='function')
def echo_plugin(event_loop):
    event_loop.run_until_complete(check_output(
        'pip install ./tests/plug-ins/echo/'
    ))
    yield
    event_loop.run_until_complete(check_output(
        'pip uninstall -y echo'
    ))


@pytest.yield_fixture(scope='function')
def server(event_loop, storage):
    cancel = asyncio.Future()
    server = event_loop.create_task(
        serve_until(cancel, storage=storage, host='127.0.0.1', port=8080)
    )
    yield '127.0.0.1:8080'
    cancel.set_result(None)
    event_loop.run_until_complete(server)


@pytest.yield_fixture(scope='function')
def client(event_loop):
    with aiohttp.ClientSession() as session:
        yield session
