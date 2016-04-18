# -*- coding: utf-8 -*-

from unittest import mock

import pkg_resources


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
    pre_receive.assert_has_calls(
        calls=[
            mock.call(
                old_ref='a',
                new_ref='b',
                target='c',
            ),
            mock.call(
                old_ref='d',
                new_ref='e',
                target='f',
            ),
        ],
        any_order=True,
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
    update.assert_has_calls(
        calls=[
           mock.call(
                target='a',
                old_ref='b',
                new_ref='c',
            ),
        ],
        any_order=True,
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
    post_receive.assert_has_calls(
        calls=[
            mock.call(
                old_ref='a',
                new_ref='b',
                target='c',
            ),
            mock.call(
                old_ref='d',
                new_ref='e',
                target='f',
            ),
        ],
        any_order=True,
    )
