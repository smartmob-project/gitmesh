# -*- coding: utf-8 -*-


import asyncio
import os
import stat
import shutil

from asyncio import subprocess
from subprocess import CalledProcessError


async def check_output(command, cwd=None, env=None,
                       input=None, binary=False, split=False):
    if isinstance(command, list):
        command = ' '.join([
            '"%s"' % arg for arg in command
        ])
    cwd = cwd or os.getcwd()
    env = env or os.environ
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd, env=env,
        stdin=None if input is None else subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE if split else subprocess.STDOUT,
    )
    output, errors = await process.communicate(input)
    if not binary:
        output = output.decode('utf-8').strip()
    status = await process.wait()
    if status != 0:
        print('OUTPUT:', output)
        raise CalledProcessError(status, command, output)
    if split:
        return output, errors
    else:
        return output


class RepositoryExists(Exception):
    pass


class UnknownRepository(Exception):
    pass


class Storage(object):
    def __init__(self, path):
        self._path = path

    @property
    def path(self):
        return self._path

    async def run(self, *args, **kwds):
        """Run a shell command inside the storage folder."""
        return await check_output(*args, cwd=self._path, **kwds)

    def _repo_path(self, name, bare=True):
        if bare:
            return os.path.join(self._path, name + '.git')
        else:
            return os.path.join(self._path, name)

    async def create_repo(self, name):
        """Create a new bare repository."""
        path = self._repo_path(name)
        try:
            os.mkdir(path)
        except FileExistsError:
            raise RepositoryExists
        await check_output(
            'git init --bare',
            cwd=path,
        )
        return Repository(name, path, bare=True)

    async def clone(self, link):
        """Clone an existing repository."""
        name = link.rsplit('/', 1)[1][:-4]
        await check_output('git clone ' + link, cwd=self._path)
        return Repository(name, self._repo_path(name, bare=False), bare=False)

    async def repository_exists(self, name):
        return os.path.isdir(self._repo_path(name))

    async def list_repositories(self):
        # TODO: run in background thread?
        return [
            name[:-4] for name in os.listdir(self._path)
            if ((not name.startswith('.')) and
                (os.path.isdir(os.path.join(self._path, name))))
        ]

    async def delete_repo(self, name):
        """Delete a repository."""
        path = self._repo_path(name)
        if not os.path.isdir(path):
            raise UnknownRepository
        shutil.rmtree(path)

    def open_repo(self, name, bare=True):
        return Repository(name, self._repo_path(name, bare=bare), bare=bare)


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

    async def run(self, *args, **kwds):
        """Run a shell command inside the repository."""
        return await check_output(*args, cwd=self._path, **kwds)

    def install_hook(self, name, data):
        """Write a hook into the repository."""
        if self.bare:
            path = os.path.join(self._path, 'hooks', name)
        else:
            path = os.path.join(self._path, '.git', 'hooks', name)
        self.edit(path, data)
        os.chmod(path, stat.S_IREAD | stat.S_IEXEC)
