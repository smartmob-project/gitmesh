# -*- coding: utf-8 -*-


import click
import importlib
import pkg_resources
import sys


def find_entry_points(group):
    for entry_point in pkg_resources.iter_entry_points(group):
        module = importlib.import_module('.'.join(
            [entry_point.module_name] + list(entry_point.attrs[:-1])
        ))
        yield entry_point.name, getattr(module, entry_point.attrs[-1])


@click.group()
def cli():
    pass


@cli.command(name='pre-receive')
def pre_receive():
    """Git pre-receive hook."""
    pre_receive_hooks = list(find_entry_points('gitmesh.pre_receive'))
    updates = [
        line.strip().split(' ', 2) for line in sys.stdin
    ]
    updates = {
        update[2]: (update[0], update[1]) for update in updates
    }
    for _, pre_receive_hook in pre_receive_hooks:
        print('Running hook %r.' % _)
        pre_receive_hook(updates=updates)


@cli.command(name='update')
@click.argument('ref')
@click.argument('old')
@click.argument('new')
def update(ref, old, new):
    """Git pre-receive hook."""
    update_hooks = list(find_entry_points('gitmesh.update'))
    for _, update_hook in update_hooks:
        print('Running hook %r.' % _)
        update_hook(ref=ref, old=old, new=new)


@cli.command(name='post-receive')
def post_receive():
    """Git post-receive hook."""
    post_receive_hooks = list(find_entry_points('gitmesh.post_receive'))
    updates = [
        line.strip().split(' ', 2) for line in sys.stdin
    ]
    updates = {
        update[2]: (update[0], update[1]) for update in updates
    }
    for _, post_receive_hook in post_receive_hooks:
        print('Running hook %r.' % _)
        post_receive_hook(updates=updates)


@cli.command(name='post-update')
@click.argument('refs', nargs=-1)
def post_update(refs):
    """Git post-update hook."""
    post_update_hooks = list(find_entry_points('gitmesh.post_update'))
    for _, post_update_hook in post_update_hooks:
        print('Running hook %r.' % _)
        post_update_hook(refs=list(refs))


def main():
    """Setuptools "console_script" entry point."""
    return cli()


# Required for `python -m gitmesh`.
if __name__ == '__main__':  # pragma: no cover
    main()
