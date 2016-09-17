# -*- coding: utf-8 -*-


import asyncio
import pytest
import structlog
import testfixtures

from freezegun import freeze_time
from gitmesh.__main__ import (
    main,
    _await,
    configure_logging,
    FluentLoggerFactory,
)
from unittest import mock


def test_main():
    with mock.patch('sys.argv', ['gitmesh', '--help']):
        with pytest.raises(SystemExit):
            main()


def test_configure_logging_stdout(capsys):
    with freeze_time("2016-05-08 21:19:00"):
        configure_logging(
            log_format='kv',
            utc=False,
            endpoint='file:///dev/stdout',
        )
        log = structlog.get_logger()
        log.info('teh.event', a=1)
    out, err = capsys.readouterr()
    assert err == ""
    assert out == "@timestamp='2016-05-08T21:19:00' event='teh.event' a=1\n"


def test_configure_logging_stderr(capsys):
    with freeze_time("2016-05-08 21:19:00"):
        configure_logging(
            log_format='kv',
            utc=False,
            endpoint='file:///dev/stderr',
        )
        log = structlog.get_logger()
        log.info('teh.event', a=1)
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "@timestamp='2016-05-08T21:19:00' event='teh.event' a=1\n"


def test_configure_logging_file(capsys, tempdir):
    with freeze_time("2016-05-08 21:19:00"):
        configure_logging(
            log_format='kv',
            utc=False,
            endpoint='file://./gitmesh.log',
        )
        log = structlog.get_logger()
        log.info('teh.event', a=1)
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
    with open('./gitmesh.log', 'r') as stream:
        logs = stream.read()
    assert logs == "@timestamp='2016-05-08T21:19:00' event='teh.event' a=1\n"


def test_configure_logging_unknown_scheme(capsys, tempdir):
    with pytest.raises(ValueError) as error:
        configure_logging(
            log_format='kv',
            utc=False,
            endpoint='flume://127.0.0.1:44444',
        )
        log = structlog.get_logger()
        log.info('teh.event', a=1)
    assert str(error.value) == \
        'Invalid logging endpoint "flume://127.0.0.1:44444".'


@pytest.mark.parametrize('log_format,expected', [
    ('kv', "@timestamp='2016-05-08T21:19:00' event='teh.event' a=1 b=2"),
    ('json', ('{"@timestamp": "2016-05-08T21:19:00"'
              ', "a": 1, "b": 2, "event": "teh.event"}')),
])
def test_log_format(log_format, expected):
    with freeze_time("2016-05-08 21:19:00"):
        with testfixtures.OutputCapture() as capture:
            configure_logging(
                log_format=log_format,
                utc=False,
                endpoint='file:///dev/stdout',
            )
            log = structlog.get_logger()
            log.info('teh.event', a=1, b=2)
        capture.compare(expected)


@pytest.mark.parametrize('url,host,port,app', [
    ('fluent://127.0.0.1:24224/the-app', '127.0.0.1', 24224, 'the-app'),
    ('fluent://127.0.0.1/the-app', '127.0.0.1', 24224, 'the-app'),
    ('fluent://127.0.0.1/', '127.0.0.1', 24224, ''),
])
def test_fluent_url_parser(url, host, port, app):
    factory = FluentLoggerFactory.from_url(url)
    assert factory.host == host
    assert factory.port == port
    assert factory.app == app


@pytest.mark.parametrize('url', [
    'fluent://127.0.0.1:abcd/the-app',
    'fluentd://127.0.0.1:abcd/the-app',  # typo in scheme.
    'fluent://127.0.0.1:24224/the-app?hello=1',  # query strings not allowed.
])
def test_fluent_url_parser_invalid_url(url):
    with pytest.raises(ValueError) as error:
        print(FluentLoggerFactory.from_url(url))
    assert str(error.value) == \
        'Invalid URL: "%s".' % (url,)


@pytest.mark.parametrize('logging_endpoint', [
    'fluent://127.0.0.1:24224/the-app',
])
@mock.patch('fluent.sender.FluentSender.emit')
def test_logging_fluentd(emit, logging_endpoint):
    with freeze_time("2016-05-08 21:19:00"):
        configure_logging(
            log_format='kv', utc=False,  # both ignored!
            endpoint=logging_endpoint,
        )
        log = structlog.get_logger()
        with testfixtures.OutputCapture() as capture:
            log.info('teh.event', a=1, b=2)
        capture.compare('')
        emit.assert_called_once_with('teh.event', {
            'a': 1,
            'b': 2,
            '@timestamp': '2016-05-08T21:19:00',
        })


def test_await(event_loop):

    def hello(name):
        return 'Hello, %s!' % name

    async def hello_coroutine(name):
        return hello(name)

    def hello_future(name):
        f = asyncio.Future(loop=event_loop)
        f.set_result(hello(name))
        return f

    assert _await(event_loop, hello('world')) == 'Hello, world!'
    assert _await(event_loop, hello_coroutine('world')) == 'Hello, world!'
    assert _await(event_loop, hello_future('world')) == 'Hello, world!'
