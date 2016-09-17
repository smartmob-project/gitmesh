# -*- coding: utf-8 -*-


import aiohttp
import aiotk
import asyncio
import click.testing
import msgpack
import os
import pytest
import testfixtures

from contextlib import contextmanager
from itertools import chain
from gitmesh import __main__
from gitmesh.storage import Storage, check_output
from gitmesh.server import serve_until
from unittest import mock


def merge_envs(lhs, rhs):
    env = {}
    env.update(lhs)
    env.update(rhs)
    return env


@contextmanager
def setenv(env):
    """Temporarily set environment variables."""
    old_environ = os.environ
    new_environ = {k: v for k, v in chain(old_environ.items(), env.items())}
    os.environ = new_environ
    try:
        yield
    finally:
        os.environ = old_environ


@pytest.fixture
def run():
    async def run(*args, **kwds):
        return await check_output(*args, **kwds)
    return run


@pytest.yield_fixture(scope='function')
def tempdir():
    old_cwd = os.getcwd()
    with testfixtures.TempDirectory(create=True) as directory:
        os.chdir(directory.path)
        yield
        os.chdir(old_cwd)
        directory.cleanup()


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
    __main__.configure_logging(log_format='kv', utc=False,
                               endpoint='file:///dev/stdout')

    # See: http://click.pocoo.org/5/testing/
    def run(loop, command, input=None, env={}):
        runner = click.testing.CliRunner()
        result = runner.invoke(
            __main__.cli, command,
            obj={
                'loop': loop,
            },
            env=env,
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
def fluent_emit():
    with mock.patch('fluent.sender.FluentSender.emit') as emit:
        yield emit


@pytest.yield_fixture(scope='function')
def fluent_env():
    env = {
        'GITMESH_LOGGING_ENDPOINT': 'fluent://127.0.0.1:24224/gitmesh',
    }
    with setenv(env):
        yield


async def service_fluent_client(records, reader, writer):
    """TCP handler for mock FluentD server.

    See:
    - https://github.com/fluent/fluentd/wiki/Forward-Protocol-Specification-v0
    - https://pythonhosted.org/msgpack-python/api.html#msgpack.Unpacker
    """
    unpacker = msgpack.Unpacker()
    data = await reader.read(1024)
    while data:
        unpacker.feed(data)
        for record in unpacker:
            records.append(record)
        data = await reader.read(1024)


@pytest.yield_fixture(scope='function')
def fluent_server(event_loop):
    """Mock FluentD server."""

    records = []

    # TODO: provide a built-in means to pass in shared server state as this
    #       wrapper will probably not cancel cleanly.
    async def service_connection(reader, writer):
        return await service_fluent_client(records, reader, writer)

    # Serve connections.
    host, port = ('127.0.0.1', 24224)
    server = aiotk.TCPServer(host, port, service_connection)
    server.start()
    event_loop.run_until_complete(server.wait_started())
    yield host, port, records
    server.close()
    event_loop.run_until_complete(server.wait_closed())


@pytest.yield_fixture(scope='function')
def server(event_loop, storage, fluent_server):
    logging_endpoint = 'fluent://%s:%d/gitmesh' % fluent_server[0:2]
    __main__.configure_logging(
        log_format='kv', utc=False,
        endpoint=logging_endpoint,
    )
    print('GITMESH_LOGGING_ENDPOINT:', logging_endpoint)

    cancel = asyncio.Future()
    with setenv({'GITMESH_LOGGING_ENDPOINT': logging_endpoint}):
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
