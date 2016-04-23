# -*- coding: utf-8 -*-


import os
import pkg_resources
import signal

from unittest import mock


class DynamicObject(object):

    def __init__(self, fields):
        self.__fields = fields

    def __getattr__(self, field):
        fields = self.__fields
        try:
            return fields[field]
        except KeyError:
            raise AttributeError(field, fields)


def test_pre_receive(cli):

    pre_receive = mock.MagicMock()

    def mock_iter_entry_points(group):
        assert group == 'gitmesh.pre_receive'
        return iter([
            # echo = echo:pre_receive
            pkg_resources.EntryPoint(
                name='echo',
                module_name='echo',
                attrs=('pre_receive',),
                extras={},
                dist='echo',
            ),
        ])

    def mock_import_module(name, package=None):
        assert name == 'echo'
        assert package is None
        return DynamicObject({
            'pre_receive': pre_receive,
        })

    # When we execute the pre-receive hook.
    with mock.patch('pkg_resources.iter_entry_points') as iter_entry_points:
        iter_entry_points.side_effect = mock_iter_entry_points
        with mock.patch('importlib.import_module') as import_module:
            import_module.side_effect = mock_import_module
            cli(['pre-receive'], input='\n'.join([
                'a b c',
                'd e f',
            ]))

    # Then it should have been invoked based on input from stdin.
    pre_receive.assert_called_once_with(
        updates={
            'c': ('a', 'b'),
            'f': ('d', 'e'),
        },
    )


def test_update(cli):

    update = mock.MagicMock()

    def mock_iter_entry_points(group):
        assert group == 'gitmesh.update'
        return iter([
            # echo = echo:update
            pkg_resources.EntryPoint(
                name='echo',
                module_name='echo',
                attrs=('update',),
                extras={},
                dist='echo',
            ),
        ])

    def mock_import_module(name, package=None):
        assert name == 'echo'
        assert package is None
        return DynamicObject({
            'update': update,
        })

    # When we execute the update hook.
    with mock.patch('pkg_resources.iter_entry_points') as iter_entry_points:
        iter_entry_points.side_effect = mock_iter_entry_points
        with mock.patch('importlib.import_module') as import_module:
            import_module.side_effect = mock_import_module
            cli(['update', 'a', 'b', 'c'])

    # Then it should have been invoked based on command-line arguments.
    update.assert_called_once_with(
        ref='a',
        old='b',
        new='c',
    )


def test_post_receive(cli):

    post_receive = mock.MagicMock()

    def mock_iter_entry_points(group):
        assert group == 'gitmesh.post_receive'
        return iter([
            # echo = echo:post_receive
            pkg_resources.EntryPoint(
                name='echo',
                module_name='echo',
                attrs=('post_receive',),
                extras={},
                dist='echo',
            ),
        ])

    def mock_import_module(name, package=None):
        assert name == 'echo'
        assert package is None
        return DynamicObject({
            'post_receive': post_receive,
        })

    # When we execute the post-receive hook.
    with mock.patch('pkg_resources.iter_entry_points') as iter_entry_points:
        iter_entry_points.side_effect = mock_iter_entry_points
        with mock.patch('importlib.import_module') as import_module:
            import_module.side_effect = mock_import_module
            cli(['post-receive'], input='\n'.join([
                'a b c',
                'd e f',
            ]))

    # Then it should have been invoked based on input from stdin.
    post_receive.assert_called_once_with(
        updates={
            'c': ('a', 'b'),
            'f': ('d', 'e'),
        },
    )


def test_post_update(cli):

    post_update = mock.MagicMock()

    def mock_iter_entry_points(group):
        assert group == 'gitmesh.post_update'
        return iter([
            # echo = echo:post_update
            pkg_resources.EntryPoint(
                name='echo',
                module_name='echo',
                attrs=('post_update',),
                extras={},
                dist='echo',
            ),
        ])

    def mock_import_module(name, package=None):
        assert name == 'echo'
        assert package is None
        return DynamicObject({
            'post_update': post_update,
        })

    # When we execute the post-update hook.
    with mock.patch('pkg_resources.iter_entry_points') as iter_entry_points:
        iter_entry_points.side_effect = mock_iter_entry_points
        with mock.patch('importlib.import_module') as import_module:
            import_module.side_effect = mock_import_module
            cli(['post-update', 'a', 'b', 'c', 'd', 'e', 'f'])

    # Then it should have been invoked based on command-line arguments.
    post_update.assert_called_once_with(
        refs=[
            'a',
            'b',
            'c',
            'd',
            'e',
            'f',
        ],
    )


def test_serve(event_loop, cli):

    # Make sure we eventually get a SIGINT/CTRL-C even.
    event_loop.call_later(1.0, os.kill, os.getpid(), signal.SIGINT)

    cli(['serve'])
