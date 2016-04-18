# -*- coding: utf-8 -*-


import os.path
import pytest


# TODO: figure out if we can symlink the installed scripts directly...

PRE_RECEIVE = """
#!/usr/bin/env sh
python3.5 -m gitmesh pre-receive
""".strip()

UPDATE = """
#!/usr/bin/env sh
python3.5 -m gitmesh update $1 $2 $3
""".strip()

POST_UPDATE = """
#!/usr/bin/env sh
python3.5 -m gitmesh post-update $@
""".strip()

POST_RECEIVE = """
#!/usr/bin/env sh
python3.5 -m gitmesh post-receive
""".strip()


def splitlines(output):
    output = output.split('\n')
    output = [line.rstrip() for line in output]
    output = [line for line in output]
    return output


@pytest.mark.asyncio
async def test_hooks(storage, workspace, run, echo_plugin):
    # Given a repository uses a bunch of hooks.
    origin = await storage.create_repo('example')
    assert origin.name == 'example'
    assert origin.path == os.path.join(storage.path, 'example.git')
    origin.install_hook('pre-receive', PRE_RECEIVE)
    origin.install_hook('update', UPDATE)
    origin.install_hook('post-update', POST_UPDATE)
    origin.install_hook('post-receive', POST_RECEIVE)
    commit0 = '0' * 40

    # And we update the master branch.
    clone = await workspace.clone(origin.path)
    assert clone.name == 'example'
    assert clone.path == os.path.join(workspace.path, 'example')
    clone.edit('README', "I'll never finish this.")
    await clone.run('git add README')
    await clone.run('git commit -m "Sets project goals."')
    commit1 = (await clone.run('git rev-parse HEAD')).strip()

    # And we update a topic branch.
    clone.edit('hot-topic.txt', "OMG, I have an idea!")
    await clone.run('git checkout -b hot-topic')
    await clone.run('git add hot-topic.txt')
    await clone.run('git commit -m "Keeps track of new idea."')
    commit2 = (await clone.run('git rev-parse HEAD')).strip()

    # When we push both branches to the repository.
    output = await clone.run('git push origin master hot-topic')

    # Then, the our hook should get executed.
    expected_lines = [
        # Changes to master branch.
        'remote: [ECHO] pre-receive refs/heads/master | %s ==> %s' % (
            commit0, commit1
        ),
        'remote: [ECHO] update refs/heads/master | %s ==> %s' % (
            commit0, commit1,
        ),
        'remote: [ECHO] post-update refs/heads/master',
        'remote: [ECHO] post-receive refs/heads/master | %s ==> %s' % (
            commit0, commit1,
        ),
        # Changes to hot-topic branch.
        'remote: [ECHO] pre-receive refs/heads/hot-topic | %s ==> %s' % (
            commit0, commit2,
        ),
        'remote: [ECHO] update refs/heads/hot-topic | %s ==> %s' % (
            commit0, commit2,
        ),
        'remote: [ECHO] post-update refs/heads/hot-topic',
        'remote: [ECHO] post-receive refs/heads/hot-topic | %s ==> %s' % (
            commit0, commit2
        ),
    ]
    actual_lines = splitlines(output)
    for line in expected_lines:
        assert line in actual_lines
