# -*- coding: utf-8 -*-


import os.path


# TODO: figure out if we can symlink the installed script directly...
PRE_RECEIVE = """
#!/usr/bin/env sh
python3.5 -m gitmesh pre-receive
""".strip()


def splitlines(output):
    output = output.split('\n')
    output = [line.rstrip() for line in output]
    output = [line for line in output]
    return output


def test_pre_receive(storage, workspace, run, echo_plugin):
    # Given a repository uses a pre-receive hook.
    origin = storage.create_repo('example')
    assert origin.name == 'example'
    assert origin.path == os.path.join(storage.path, 'example.git')
    origin.install_hook('pre-receive', PRE_RECEIVE)

    # When we push to the repository.
    clone = workspace.clone(origin.path)
    assert clone.name == 'example'
    assert clone.path == os.path.join(workspace.path, 'example')
    clone.edit('README', "I'll never finish this.")
    clone.run('git add README')
    clone.run('git commit -m "Sets project goals."')
    output = clone.run('git push origin master')

    # Then, the pre-receive hook should be executed.
    lines = splitlines(output)
    assert 'remote: [ECHO] pre-receive' in lines
