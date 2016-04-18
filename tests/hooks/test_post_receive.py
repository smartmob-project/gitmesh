# -*- coding: utf-8 -*-


import os.path


# TODO: figure out if we can symlink the installed script directly...
POST_RECEIVE = """
#!/usr/bin/env sh
python3.5 -m gitmesh post-receive
""".strip()


def splitlines(output):
    output = output.split('\n')
    output = [line.rstrip() for line in output]
    output = [line for line in output]
    return output


def test_post_receive(storage, workspace, run, echo_plugin):
    # Given a repository uses a post-receive hook.
    origin = storage.create_repo('example')
    assert origin.name == 'example'
    assert origin.path == os.path.join(storage.path, 'example.git')
    origin.install_hook('post-receive', POST_RECEIVE)

    # When we push to the repository.
    clone = workspace.clone(origin.path)
    assert clone.name == 'example'
    assert clone.path == os.path.join(workspace.path, 'example')
    clone.edit('README', "I'll never finish this.")
    clone.run('git add README')
    clone.run('git commit -m "Sets project goals."')
    output = clone.run('git push origin master')

    # Then, the post-receive hook should be executed.
    lines = splitlines(output)
    assert 'remote: [ECHO] post-receive' in lines
