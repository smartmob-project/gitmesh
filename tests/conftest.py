# -*- coding: utf-8 -*-


import click.testing
import os
import pytest
import stat
import subprocess
import testfixtures

from gitmesh import __main__


def check_output(command, cwd=None, env=None):
    cwd = cwd or os.getcwd()
    env = env or os.environ
    process = subprocess.Popen(
        command, shell=True,
        cwd=cwd, env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output, _ = process.communicate()
    output = output.decode('utf-8').strip()
    status = process.wait()
    if status != 0:
        raise Exception('Command %r failed with status %r and output %r.' % (
            command,
            status,
            output,
        ))
    return output


def merge_envs(lhs, rhs):
    env = {}
    env.update(lhs)
    env.update(rhs)
    return env


@pytest.fixture
def run():
    def run(*args, **kwds):
        return check_output(*args, **kwds)
    return run


class Storage(object):
    def __init__(self, path):
        self._path = path

    @property
    def path(self):
        return self._path

    def create_repo(self, name):
        """Create a new bare repository."""
        path = os.path.join(self._path, name + '.git')
        os.mkdir(path)
        check_output(
            'git init --bare',
            cwd=path,
        )
        return Repository(name, path, bare=True)

    def clone(self, link):
        """Clone an existing repository."""
        name = link.rsplit('/', 1)[1][:-4]
        check_output('git clone ' + link, cwd=self._path)
        return Repository(name, os.path.join(self._path, name), bare=False)


class Repository(object):
    def __init__(self, name, path, bare):
        self._name = name
        self._path = path
        self._bare = bare

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def bare(self):
        return self._bare

    def edit(self, path, data):
        """Write to a file inside the working tree."""
        with open(os.path.join(self._path, path), 'w') as stream:
            stream.write(data)

    def run(self, *args, **kwds):
        """Run a shell command inside the repository."""
        return check_output(*args, cwd=self._path, **kwds)

    def install_hook(self, name, data):
        """Symlink a hook into the repository."""
        if self.bare:
            path = os.path.join(self._path, 'hooks', name)
        else:
            path = os.path.join(self._path, '.git', 'hooks', name)
        self.edit(path, data)
        os.chmod(path, stat.S_IREAD | stat.S_IEXEC)


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


@pytest.yield_fixture(scope='module')
def echo_plugin():
    check_output('pip install ./tests/plug-ins/echo/')
    yield
    check_output('pip uninstall -y echo')
