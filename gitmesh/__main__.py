# -*- coding: utf-8 -*-


import asyncio
import click
import importlib
import pkg_resources
import signal
import structlog
import structlog.processors
import sys

from inspect import iscoroutine

from gitmesh.server import serve_until
from gitmesh.storage import Storage


def find_entry_points(group):
    for entry_point in pkg_resources.iter_entry_points(group):
        module = importlib.import_module('.'.join(
            [entry_point.module_name] + list(entry_point.attrs[:-1])
        ))
        yield entry_point.name, getattr(module, entry_point.attrs[-1])


def configure_logging(log_format, utc):
    processors = [
        structlog.processors.TimeStamper(
            fmt='iso',
            key='@timestamp',
            utc=utc,
        ),
    ]
    if log_format == 'kv':
        processors.append(structlog.processors.KeyValueRenderer(
            sort_keys=True,
            key_order=['@timestamp', 'event'],
        ))
    else:
        processors.append(structlog.processors.JSONRenderer(
            sort_keys=True,
        ))
    structlog.configure(
        processors=processors,
    )


@click.group()
# @click.option('--log-level', default='debug',
#               type=click.Choice(['debug', 'info', 'warning', 'error']))
@click.option('--log-format', default='kv',
              type=click.Choice(['kv', 'json']))
@click.option('--utc-timestamps', default=True, type=bool)
@click.pass_context
def cli(ctx, log_format, utc_timestamps):
    # Initialize logger.
    configure_logging(
        log_format=log_format,
        utc=utc_timestamps,
    )
    log = structlog.get_logger()

    # Pick the right event loop.
    if sys.platform == 'win32':  # pragma: no cover
        asyncio.set_event_loop(asyncio.ProactorEventLoop())
    loop = asyncio.get_event_loop()
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

    loop = asyncio.get_event_loop()
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


@cli.command(name='update')
@click.argument('ref')
@click.argument('old')
@click.argument('new')
@click.pass_context
def update(ctx, ref, old, new):
    """Git pre-receive hook."""

    log = ctx.obj['log']
    log.info('git.hooks.update', ref=ref, old_sha=old, new_sha=new)

    loop = asyncio.get_event_loop()
    update_hooks = list(find_entry_points('gitmesh.update'))
    for _, update_hook in update_hooks:
        print('Running hook %r.' % _)
        _await(loop, update_hook(ref=ref, old=old, new=new))


@cli.command(name='post-receive')
@click.pass_context
def post_receive(ctx):
    """Git post-receive hook."""

    log = ctx.obj['log']
    log.info('git.hooks.post-receive')

    loop = asyncio.get_event_loop()
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


@cli.command(name='post-update')
@click.argument('refs', nargs=-1)
@click.pass_context
def post_update(ctx, refs):
    """Git post-update hook."""

    log = ctx.obj['log']
    log.info('git.hooks.post-update', refs=refs)

    loop = asyncio.get_event_loop()
    post_update_hooks = list(find_entry_points('gitmesh.post_update'))
    for hook_name, post_update_hook in post_update_hooks:
        log.info(event='git.hooks.post_update', hook=hook_name)
        _await(loop, post_update_hook(refs=list(refs)))


@cli.command(name='serve')
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=8080)
@click.pass_context
def serve(ctx, host, port):
    """Run the server until SIGINT/CTRL-C is received."""

    log = ctx.obj['log']
    log.info('serve', host=host, port=port)

    loop = asyncio.get_event_loop()

    # Await a SIGINT/CTRL-C event.
    cancel = asyncio.Future()
    if sys.platform == 'win32':  # pragma: no cover
        pass
    else:
        loop.add_signal_handler(signal.SIGINT, cancel.set_result, None)

    # Serve "forever".
    loop.run_until_complete(serve_until(
        cancel,
        storage=Storage('.'),
        host=host, port=port, log=log,
    ))


def main():
    """Setuptools "console_script" entry point."""
    loop = asyncio.get_event_loop()
    try:
        return cli(obj={})
    finally:
        loop.close()


# Required for `python -m gitmesh`.
if __name__ == '__main__':  # pragma: no cover
    main()
