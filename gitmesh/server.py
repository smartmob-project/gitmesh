# -*- coding: utf-8 -*-


import asyncio
import json
import os
import structlog
import timeit
import uuid

from aiohttp import web
from datetime import datetime, timezone
from voluptuous import Schema, Required, MultipleInvalid

from gitmesh.storage import (
    RepositoryExists,
    UnknownRepository,
)


async def inject_request_id(app, handler):
    """aiohttp middleware: ensures each request has a unique request ID.

    See: ``inject_request_id``.
    """

    async def trace_request(request):
        request['x-request-id'] = \
            request.headers.get('x-request-id') or str(uuid.uuid4())
        return await handler(request)

    return trace_request


async def echo_request_id(request, response):
    """aiohttp signal: ensures each response contains the request ID.

    See: ``echo_request_id``.
    """
    response.headers['x-request-id'] = request.get('x-request-id', '?')


async def access_log_middleware(app, handler):
    """Log each request in structured event log."""

    event_log = app.get('gitmesh.event_log') or structlog.get_logger()
    clock = app.get('gitmesh.clock') or timeit.default_timer

    # Keep the request arrival time to ensure we get intuitive logging of
    # events.
    arrival_time = datetime.utcnow().replace(tzinfo=timezone.utc)

    async def access_log(request):
        ref = clock()
        try:
            response = await handler(request)
            event_log.info(
                'http.access',
                path=request.path,
                outcome=response.status,
                duration=(clock()-ref),
                request=request.get('x-request-id', '?'),
                **{'@timestamp': arrival_time},
            )
            return response
        except web.HTTPException as error:
            event_log.info(
                'http.access',
                path=request.path,
                outcome=error.status,
                duration=(clock()-ref),
                request=request.get('x-request-id', '?'),
                **{'@timestamp': arrival_time},
            )
            raise
        except Exception:
            event_log.info(
                'http.access',
                path=request.path,
                outcome=500,
                duration=(clock()-ref),
                request=request.get('x-request-id', '?'),
                **{'@timestamp': arrival_time},
            )
            raise

    return access_log


Index = Schema({
    Required('list'): str,  # GET to query repository listing.
    Required('create'): str,  # POST to create new repository.
})


RepositoryDetails = Schema({
    Required('name'): str,  # name of the project.
    Required('clone'): [str],
    Required('details'): str,  # GET to refresh snapshot.
    Required('delete'): str,  # POST here to delete.
})


RepositoryListing = Schema({
    'repositories': [RepositoryDetails],
})


CreateRequest = Schema({
    Required('name'): str,
    'clone_url': str,  # will `git clone` this.
})


def _listing_url(request):
    return '%s://%s%s' % (
        request.scheme,
        request.host,
        request.app.router['list-repositories'].url(),
    )


def _clone_url(request, name):
    return '%s://%s%s' % (
        request.scheme,
        request.host,
        request.app.router['git-http-endpoint'].url(parts=dict(
            name=name,
            path='/',
        )),
    )


def _create_url(request):
    return '%s://%s%s' % (
        request.scheme,
        request.host,
        request.app.router['create-repository'].url(),
    )


def _delete_url(request, name):
    return '%s://%s%s' % (
        request.scheme,
        request.host,
        request.app.router['delete-repository'].url(parts=dict(
            name=name,
        )),
    )


def _details_url(request, name):
    return '%s://%s%s' % (
        request.scheme,
        request.host,
        request.app.router['get-repository'].url(parts=dict(
            name=name,
        )),
    )


async def index(request):
    """."""

    log = request.app['gitmesh.event_log']
    log.info('api.list-repositories')

    return web.json_response(Index({
        'list': _listing_url(request),
        'create': _create_url(request),
    }))


async def list_repositories(request):
    """."""

    storage = request.app['gitmesh.storage']
    repository_names = await storage.list_repositories()

    # Format the response.
    return web.json_response({
        'repositories': [
            {
                'name': name,
                'clone': [
                    _clone_url(request, name),
                ],
                'details': _details_url(request, name),
                'delete': _delete_url(request, name),
            }
            for name in sorted(repository_names)
        ],
    })


async def create_repository(request):
    """."""

    log = request.app['gitmesh.event_log']

    # Validate request.
    r = await request.json()
    try:
        r = CreateRequest(r)
    except MultipleInvalid:
        raise web.HTTPBadRequest
    name = r['name']

    # Create the project.
    storage = request.app['gitmesh.storage']
    try:
        await storage.create_repo(name, install_hooks=True)
    except RepositoryExists:
        raise web.HTTPConflict()

    log.info('repository.create', name=name)

    # Format response.
    return web.HTTPCreated(
        content_type='application/json',
        body=json.dumps(RepositoryDetails({
            'name': name,
            'clone': [
                _clone_url(request, name),
            ],
            'details': _details_url(request, name),
            'delete': _delete_url(request, name),
        })).encode('utf-8'),
        headers={
            'Location': _details_url(request, name),
        },
    )


async def query_repository(request):
    """."""

    # Validate request.
    name = request.match_info['name']

    # Check that the repository exists.
    storage = request.app['gitmesh.storage']
    exists = await storage.repository_exists(name)
    if not exists:
        raise web.HTTPNotFound

    # Format response.
    return web.json_response(RepositoryDetails({
        'name': name,
        'clone': [
            _clone_url(request, name),
        ],
        'details': _details_url(request, name),
        'delete': _delete_url(request, name),
    }))


async def delete_repository(request):
    """."""

    log = request.app['gitmesh.event_log']

    # Validate request.
    name = request.match_info['name']

    log.info('repository.delete', name=name)

    # Delete the repository.
    storage = request.app['gitmesh.storage']
    try:
        await storage.delete_repo(name)
    except UnknownRepository:
        raise web.HTTPNotFound

    # Format the response.
    return web.json_response({})


async def git_http_endpoint(request):

    log = request.app['gitmesh.event_log']

    # Validate request.
    name = request.match_info['name']
    path = request.match_info['path']
    data = await request.read()
    storage = request.app['gitmesh.storage']
    repo = storage.open_repo(name, bare=True)

    # TODO:
    # - authenticate on POST.
    env = dict(os.environ.items())
    env.update({
        'CONTENT_LENGTH': str(len(data)),
        'CONTENT_TYPE': request.content_type,
        'GATEWAY_INTERFACE': 'CGI/1.1',
        'PATH_INFO': path,
        'QUERY_STRING': request.query_string,
        'REMOTE_ADDR': request.transport.get_extra_info('peername')[0],
        'REMOTE_USER': 'acaron',
        'REQUEST_METHOD': request.method,
        # 'AUTH_TYPE': '',
        # 'PATH_TRANSLATED': '',
        # 'REMOTE_HOST': '',
        # 'REMOTE_IDENT': '',
        # 'SCRIPT_NAME': '',
        # 'SERVER_NAME': '',
        # 'SERVER_PORT': '',
        # 'SERVER_PROTOCOL': '',
        # 'SERVER_SOFTWARE': '',
        # Custom.
        'GITMESH_REQUEST_ID': request['x-request-id'],
    })
    # env.update({
    # 'HTTP_'
    # })
    env.update({
        'GIT_PROJECT_ROOT': '.',
        'GIT_HTTP_EXPORT_ALL': '1',
    })

    # Execute the CGI script.
    log.info('git-http-backend.run')
    output, errors = await repo.run(
        'git http-backend',
        input=data,
        binary=True,
        env=env,
        split=True,
    )

    # Format response.
    head, body = output.split(b'\r\n\r\n', 1)
    head = dict(
        line.split(':', 1)
        for line in head.decode('utf-8').split('\r\n')
    )
    status = head.get('Status', '200 OK').strip()
    status = int(status.split(' ', 1)[0])
    log.info('git-http-backend.done',
             status=status, errors=errors, head=head)
    return web.Response(status=status, headers=head, body=body)


async def serve_until(cancel, *, storage, host, port, linger=1.0, log=None,
                      loop=None):
    log = log or structlog.get_logger()
    loop = loop or asyncio.get_event_loop()

    # Prepare a web application.
    app = web.Application(loop=loop, middlewares=[
        inject_request_id,
        access_log_middleware,
    ])
    app.on_response_prepare.append(echo_request_id)
    app.router.add_route('GET', '/', index, name='index')
    app.router.add_route('GET', '/repositories',
                         list_repositories, name='list-repositories')
    app.router.add_route('POST', '/repositories',
                         create_repository, name='create-repository')
    app.router.add_route('*', '/repositories/{name}.git{path:.+}',
                         git_http_endpoint, name='git-http-endpoint')
    app.router.add_route('GET', '/repositories/{name}',
                         query_repository, name='get-repository')
    app.router.add_route('DELETE', '/repositories/{name}',
                         delete_repository, name='delete-repository')

    # Inject context.
    app['gitmesh.event_log'] = log
    app['gitmesh.storage'] = storage
    app['gitmesh.clock'] = timeit.default_timer

    # Start accepting connections.
    handler = app.make_handler()
    log.info(event='bind', transport='tcp', host=host, port=port)
    server = await loop.create_server(handler, host, port)
    try:
        log.info(event='ready')
        await cancel
    finally:
        log.info(event='shutdown', linger=linger, expected=cancel.done())
        server.close()
        await server.wait_closed()
        await handler.finish_connections(linger)
        await app.finish()
        log.info(event='done')
