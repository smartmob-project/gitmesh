# -*- coding: utf-8 -*-


import os.path
import pytest
import sys

from subprocess import CalledProcessError

from gitmesh.storage import check_output


here = os.path.dirname(os.path.abspath(__file__))


def readfile(path):
    with open(path, 'r') as stream:
        return stream.read()


@pytest.mark.asyncio
async def test_check_output_success():
    output = await check_output([
        sys.executable,
        os.path.join(here, 'exit-success.py'),
    ])
    assert output.strip() == '\n'.join([
        'STDOUT: 1',
        'STDERR: 2',
        'STDOUT: 3',
    ])


@pytest.mark.asyncio
async def test_check_output_failure():
    with pytest.raises(CalledProcessError) as exc:
        print(await check_output([
            sys.executable,
            os.path.join(here, 'exit-failure.py'),
            '1',
        ]))
    assert exc.value.returncode == 1
    assert exc.value.output == '\n'.join([
        'STDOUT: 1',
        'STDERR: 2',
        'STDOUT: 3',
    ])


@pytest.mark.asyncio
async def test_create_repository(storage):
    expected_path = os.path.join(storage.path, 'foo.git')

    # Given the repo does not exist.
    assert not os.path.isdir(expected_path)

    # When we create it.
    repo = await storage.create_repo('foo')

    # Then it should exist.
    assert repo.path == expected_path
    assert repo.bare
    assert os.path.isdir(expected_path)


@pytest.mark.asyncio
async def test_clone(storage, workspace):
    expected_path = os.path.join(workspace.path, 'foo')

    # Given there is a remote repository.
    repo = await storage.create_repo('foo')

    # But we don't have a local copy.
    assert not os.path.isdir(expected_path)

    # When we clone it.
    fork = await workspace.clone(repo.path)

    # Then we should have a local copy.
    assert fork.path == expected_path
    assert not fork.bare
    assert os.path.isdir(expected_path)


@pytest.mark.asyncio
async def test_edit(storage, workspace):
    # Given we have a local repository.
    repo = await storage.create_repo('foo')
    fork = await workspace.clone(repo.path)

    # When we write file into it.
    fork.edit('README', 'Hello!')

    # Then the file should exist and contain the expected contents.
    assert readfile(os.path.join(fork.path, 'README')) == 'Hello!'


@pytest.mark.asyncio
async def test_run(storage, workspace):
    # Given we have a local repository.
    repo = await storage.create_repo('foo')
    fork = await workspace.clone(repo.path)

    # When we run a command inside it.
    output = await fork.run([
        sys.executable,
        os.path.join(here, 'pwd.py'),
    ])

    # Then the command should have been run inside the repository.
    assert output.strip() == os.path.realpath(fork.path)


@pytest.mark.asyncio
async def test_install_server_hook(storage):
    # Given we have a remote repository.
    repo = await storage.create_repo('foo')

    # And it has a hook
    repo.install_hook(
        'pre-receive',
        '\n'.join([
            '#!' + sys.executable,
            'print("Hello!")',
        ]),
        method='data',
    )

    # When we execute the hook.
    output = await repo.run(os.path.join(
        repo.path, 'hooks', 'pre-receive',
    ))

    # Then it should run as expected.
    assert output.strip() == 'Hello!'


@pytest.mark.asyncio
async def test_install_client_hook(storage, workspace):
    # Given we have a local repository.
    repo = await storage.create_repo('foo')
    fork = await workspace.clone(repo.path)

    # And it has a hook
    fork.install_hook(
        'pre-receive',
        '\n'.join([
            '#!' + sys.executable,
            'print("Hello!")',
        ]),
        method='data',
    )

    # When we execute the hook.
    output = await fork.run(os.path.join(
        fork.path, '.git', 'hooks', 'pre-receive',
    ))

    # Then it should run as expected.
    assert output.strip() == 'Hello!'
