# -*- coding: utf-8 -*-


import json
import logging
import pytest


@pytest.mark.asyncio
async def test_create_repository(server, client):
    # Given the server is running.
    async with client.get('http://%s/' % server) as rep:
        assert rep.status == 200
        index = await rep.json()

    # And we try to create a new repository.
    req = json.dumps({
        'name': 'foo',
    }).encode('utf-8')
    async with client.post(index['create'], data=req) as rep:
        repo = await rep.json()

        # Then it should exist.
        assert repo == {
            'name': 'foo',
            'clone': [
                'http://%s/repositories/foo.git/' % server,
            ],
            'details': 'http://%s/repositories/foo' % server,
            'delete': 'http://%s/repositories/foo' % server,
        }


@pytest.mark.asyncio
async def test_create_existing_repository(server, client):
    # Given the server is running.
    async with client.get('http://%s/' % server) as rep:
        assert rep.status == 200
        index = await rep.json()

    # And the repository exists.
    req = json.dumps({
        'name': 'foo',
    }).encode('utf-8')
    async with client.post(index['create'], data=req) as rep:
        repo = await rep.json()
        assert repo == {
            'name': 'foo',
            'clone': [
                'http://%s/repositories/foo.git/' % server,
            ],
            'details': 'http://%s/repositories/foo' % server,
            'delete': 'http://%s/repositories/foo' % server,
        }

    # When we try to create it again.
    req = json.dumps({
        'name': 'foo',
    }).encode('utf-8')
    async with client.post(index['create'], data=req) as rep:

        # Then the request should be rejected.
        assert rep.status == 409


@pytest.mark.asyncio
async def test_create_repository_invalid_request(server, client):
    # Given the server is running.
    async with client.get('http://%s/' % server) as rep:
        assert rep.status == 200
        index = await rep.json()

    # And we try to create a new repository with an invalid request.
    req = json.dumps({
        'nme': 'foo',  # NOTE: intentional typo.
    }).encode('utf-8')
    async with client.post(index['create'], data=req) as rep:

        # Them the request should be rejected.
        assert rep.status == 400


@pytest.mark.asyncio
async def test_query_repository(server, client):
    # Given the server is running.
    async with client.get('http://%s/' % server) as rep:
        assert rep.status == 200
        index = await rep.json()

    # And the repository exists.
    req = json.dumps({
        'name': 'foo',
    }).encode('utf-8')
    async with client.post(index['create'], data=req) as rep:
        repo = await rep.json()
        assert repo == {
            'name': 'foo',
            'clone': [
                'http://%s/repositories/foo.git/' % server,
            ],
            'details': 'http://%s/repositories/foo' % server,
            'delete': 'http://%s/repositories/foo' % server,
        }

    # When we fetch the details.
    async with client.get(repo['details']) as rep:

        # Then we should get the info we got when we created it.
        assert rep.status == 200
        body = await rep.json()
        assert body == repo


@pytest.mark.asyncio
async def test_query_unknown_repository(server, client):
    # Given the server is running.
    async with client.get('http://%s/' % server) as rep:
        assert rep.status == 200

    # But the repository does not exist.
    details = 'http://%s/repositories/foo' % server

    # When we fetch the details.
    async with client.get(details) as rep:

        # Then the request should fail.
        assert rep.status == 404


@pytest.mark.asyncio
async def test_repository_listing(server, client):
    # Given the server is running.
    async with client.get('http://%s/' % server) as rep:
        assert rep.status == 200
        index = await rep.json()

    # But there are no repositories.

    # When we fetch the listing.
    async with client.get(index['list']) as rep:
        assert rep.status == 200
        listing = await rep.json()

        # Then the listing is empty.
        assert listing == {
            'repositories': [],
        }

    # Given a pair of repositories exist.
    req = json.dumps({
        'name': 'foo',
    }).encode('utf-8')
    async with client.post(index['create'], data=req) as rep:
        assert rep.status == 201
        foo = await rep.json()
    req = json.dumps({
        'name': 'bar',
    }).encode('utf-8')
    async with client.post(index['create'], data=req) as rep:
        assert rep.status == 201
        bar = await rep.json()

    # When we fetch the listing.
    async with client.get(index['list']) as rep:
        assert rep.status == 200
        listing = await rep.json()

        # Then the listing shows our two repositories.
        assert listing == {
            'repositories': [
                bar,
                foo,
            ],
        }


@pytest.mark.asyncio
async def test_delete_repository(server, client):
    # Given the server is running.
    async with client.get('http://%s/' % server) as rep:
        assert rep.status == 200
        index = await rep.json()

    # And a pair of repositories exist.
    req = json.dumps({
        'name': 'foo',
    }).encode('utf-8')
    async with client.post(index['create'], data=req) as rep:
        assert rep.status == 201
        foo = await rep.json()
    req = json.dumps({
        'name': 'bar',
    }).encode('utf-8')
    async with client.post(index['create'], data=req) as rep:
        assert rep.status == 201
        bar = await rep.json()

    # When we fetch the listing.
    async with client.get(index['list']) as rep:
        assert rep.status == 200
        listing = await rep.json()

        # Then the listing shows our two repositories.
        assert listing == {
            'repositories': [
                bar,
                foo,
            ],
        }

    # When we delete one of the repositories.
    async with client.delete(foo['delete']) as rep:
        assert rep.status == 200
        body = await rep.json()
        assert body == {}

    # And we fetch the listing.
    async with client.get(index['list']) as rep:
        assert rep.status == 200
        listing = await rep.json()

        # Then the listing shows only the remaining repository.
        assert listing == {
            'repositories': [
                bar,
            ],
        }


@pytest.mark.asyncio
async def test_delete_unknown_repository(server, client):
    # Given the server is running.
    async with client.get('http://%s/' % server) as rep:
        assert rep.status == 200

    # But the repository does not exist.
    delete = 'http://%s/repositories/foo' % server

    # When we delete the repository.
    async with client.delete(delete) as rep:

        # Then the request fails.
        assert rep.status == 404


@pytest.mark.asyncio
async def test_clone_repository(server, client, run, workspace):
    # Given the server is running.
    async with client.get('http://%s/' % server) as rep:
        assert rep.status == 200
        index = await rep.json()

    # And a repository exists.
    req = json.dumps({
        'name': 'foo',
    }).encode('utf-8')
    async with client.post(index['create'], data=req) as rep:
        repo = await rep.json()

        # Then it should exist.
        assert repo == {
            'name': 'foo',
            'clone': [
                'http://%s/repositories/foo.git/' % server,
            ],
            'details': 'http://%s/repositories/foo' % server,
            'delete': 'http://%s/repositories/foo' % server,
        }

    # When we try to clone it.
    logging.debug('FOO')
    await workspace.run('git clone ' + repo['clone'][0])

    # Then we should be able to push to it.
    repo = workspace.open_repo(repo['name'], bare=False)
    await repo.run('git config user.name "py.test"')
    await repo.run('git config user.email "noreply@example.org"')
    repo.edit('README.txt', 'Nothing to see here!')
    await repo.run('git add README.txt')
    await repo.run('git commit -m "Starts project."')
    await repo.run('git push origin master')
