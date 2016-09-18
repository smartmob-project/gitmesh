# -*- coding: utf-8 -*-


import asyncio
import click
import fluent.sender
import importlib
import pkg_resources
import signal
import structlog
import structlog.processors
import sys

from datetime import datetime, timezone
from inspect import iscoroutine
from urllib.parse import urlsplit

from gitmesh.server import serve_until
from gitmesh.storage import Storage


def find_entry_points(group):
    for entry_point in pkg_resources.iter_entry_points(group):
        module = importlib.import_module('.'.join(
            [entry_point.module_name] + list(entry_point.attrs[:-1])
        ))
        yield entry_point.name, getattr(module, entry_point.attrs[-1])


class FluentLoggerFactory:
    """For use with ``structlog.configure(logger_factory=...)``."""

    @classmethod
    def from_url(cls, url):
        parts = urlsplit(url)
        if parts.scheme != 'fluent':
            raise ValueError('Invalid URL: "%s".' % url)
        if parts.query or parts.fragment:
            raise ValueError('Invalid URL: "%s".' % url)
        netloc = parts.netloc.rsplit(':', 1)
        if len(netloc) == 1:
            host, port = netloc[0], 24224
        else:
            host, port = netloc
            try:
                port = int(port)
            except ValueError:
                raise ValueError('Invalid URL: "%s".' % url)
        return FluentLoggerFactory(parts.path[1:], host, port)

    def __init__(self, app, host, port):
        self._app = app
        self._host = host
        self._port = port
        self._sender = fluent.sender.FluentSender(app, host=host, port=port)

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def app(self):
        return self._app

    def __call__(self):
        return FluentLogger(self._sender)


class FluentLogger:
    """Structlog logger that sends events to FluentD."""

    def __init__(self, sender):
        self._sender = sender

    def info(self, event, **kwds):
        self._sender.emit(event, kwds)


class TimeStamper(object):
    """Custom implementation of ``structlog.processors.TimeStamper``.

    See:
    - https://github.com/hynek/structlog/issues/81
    """

    def __init__(self, key, utc):
        self._key = key
        self._utc = utc
        if utc:
            def now():
                return datetime.utcnow().replace(tzinfo=timezone.utc)
        else:
            def now():
                return datetime.now()
        self._now = now

    def __call__(self, _, __, event_dict):
        timestamp = event_dict.get('@timestamp')
        if timestamp is None:
            timestamp = self._now()
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        event_dict['@timestamp'] = timestamp
        return event_dict


def configure_logging(log_format, utc, endpoint):
    processors = [
        TimeStamper(
            key='@timestamp',
            utc=utc,
        ),
    ]
    if endpoint.startswith('file://'):
        path = endpoint[7:]
        if path == '/dev/stdout':
            stream = sys.stdout
        elif path == '/dev/stderr':
            stream = sys.stderr
        else:
            stream = open(path, 'w')
        logger_factory = structlog.PrintLoggerFactory(file=stream)
        if log_format == 'kv':
            processors.append(structlog.processors.KeyValueRenderer(
                sort_keys=True,
                key_order=['@timestamp', 'event'],
            ))
        else:
            processors.append(structlog.processors.JSONRenderer(
                sort_keys=True,
            ))
    elif endpoint.startswith('fluent://'):
        utc = True
        logger_factory = FluentLoggerFactory.from_url(endpoint)
    else:
        raise ValueError('Invalid logging endpoint "%s".' % endpoint)
    structlog.configure(
        processors=processors,
        logger_factory=logger_factory,
    )


# TODO: turn --log-format and --logging-endpoint arguments into query string
#       parameters of file:/// URL.
@click.group()
# @click.option('--log-level', default='debug',
#               type=click.Choice(['debug', 'info', 'warning', 'error']))
@click.option('--log-format', default='kv',
              type=click.Choice(['kv', 'json']))
@click.option('--utc-timestamps', default=True, type=bool)
@click.option('--logging-endpoint',
              default='file:///dev/stdout',
              envvar='GITMESH_LOGGING_ENDPOINT')
@click.pass_context
def cli(ctx, log_format, utc_timestamps, logging_endpoint):

    # Initialize logger.
    configure_logging(
        endpoint=logging_endpoint,
        log_format=log_format,
        utc=utc_timestamps,
    )
    log = structlog.get_logger()

    # Pick the right event loop (unless it's already set).
    loop = ctx.obj.get('loop')
    if not loop:
        if sys.platform == 'win32':  # pragma: no cover
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        loop = asyncio.get_event_loop()
        ctx.obj['loop'] = loop
    log.info('asyncio.init', loop=loop.__class__.__name__)

    # Inject context.
    ctx.obj['log'] = log


def _await(loop, r):
    """Await expression for regular functions."""
    if iscoroutine(r) or isinstance(r, asyncio.Future):
        r = loop.run_until_complete(r)
    return r


@cli.command(name='pre-receive')
@click.pass_context
def pre_receive(ctx):
    """Git pre-receive hook."""

    log = ctx.obj['log']
    log.info('git.hooks.pre-receive')

    loop = ctx.obj['loop']
    try:
        pre_receive_hooks = list(find_entry_points('gitmesh.pre_receive'))
        updates = [
            line.strip().split(' ', 2) for line in sys.stdin
        ]
        updates = {
            update[2]: (update[0], update[1]) for update in updates
        }
        for _, pre_receive_hook in pre_receive_hooks:
            print('Running hook %r.' % _)
            _await(loop, pre_receive_hook(updates=updates))
    finally:
        loop.close()


@cli.command(name='update')
@click.argument('ref')
@click.argument('old')
@click.argument('new')
@click.pass_context
def update(ctx, ref, old, new):
    """Git pre-receive hook."""

    log = ctx.obj['log']
    log.info('git.hooks.update', ref=ref, old_sha=old, new_sha=new)

    loop = ctx.obj['loop']
    try:
        update_hooks = list(find_entry_points('gitmesh.update'))
        for _, update_hook in update_hooks:
            print('Running hook %r.' % _)
            _await(loop, update_hook(ref=ref, old=old, new=new))
    finally:
        loop.close()


@cli.command(name='post-receive')
@click.pass_context
def post_receive(ctx):
    """Git post-receive hook."""

    log = ctx.obj['log']
    log.info('git.hooks.post-receive')

    loop = ctx.obj['loop']
    try:
        post_receive_hooks = list(find_entry_points('gitmesh.post_receive'))
        updates = [
            line.strip().split(' ', 2) for line in sys.stdin
        ]
        updates = {
            update[2]: (update[0], update[1]) for update in updates
        }
        for hook_name, post_receive_hook in post_receive_hooks:
            log.info(event='post_update', hook=hook_name)
            _await(loop, post_receive_hook(updates=updates))
    finally:
        loop.close()


@cli.command(name='post-update')
@click.argument('refs', nargs=-1)
@click.pass_context
def post_update(ctx, refs):
    """Git post-update hook."""

    log = ctx.obj['log']
    log.info('git.hooks.post-update', refs=refs)

    loop = ctx.obj['loop']
    try:
        post_update_hooks = list(find_entry_points('gitmesh.post_update'))
        for hook_name, post_update_hook in post_update_hooks:
            log.info(event='git.hooks.post_update', hook=hook_name)
            _await(loop, post_update_hook(refs=list(refs)))
    finally:
        loop.close()


@cli.command(name='serve')
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=8080)
@click.pass_context
def serve(ctx, host, port):
    """Run the server until SIGINT/CTRL-C is received."""

    log = ctx.obj['log']
    log.info('serve', host=host, port=port)

    loop = ctx.obj['loop']

    # Await a SIGINT/CTRL-C event.
    cancel = asyncio.Future(loop=loop)
    if sys.platform == 'win32':  # pragma: no cover
        pass
    else:
        loop.add_signal_handler(signal.SIGINT, cancel.set_result, None)

    # Serve "forever".
    loop.run_until_complete(serve_until(
        cancel,
        storage=Storage('.'),
        host=host, port=port, log=log, loop=loop,
    ))


def main():
    """Setuptools "console_script" entry point."""
    return cli(obj={})


# Required for `python -m gitmesh`.
if __name__ == '__main__':  # pragma: no cover
    main()
