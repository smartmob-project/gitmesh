# -*- coding: utf-8 -*-


import pytest

from aiohttp import web
from gitmesh.server import (
    access_log_middleware,
    inject_request_id,
    echo_request_id,
)
from unittest import mock


# TODO: find a better way to write these tests (more akin to ``WebTest``).


@pytest.mark.asyncio
async def test_middleware_success_200():

    event_log = mock.MagicMock()
    clock = mock.MagicMock()
    clock.side_effect = [0.0, 1.0]
    app = {
        'gitmesh.event_log': event_log,
        'gitmesh.clock': clock,
    }

    def mock_get(k, d):
        assert k.lower() == 'x-request-id'
        assert d == '?'
        return '123'

    req = mock.MagicMock(autospec=web.Request)
    req.path = '/'
    req.get.side_effect = mock_get
    rep = web.Response(body=b'...')

    async def index(request):
        assert request is req
        return rep

    handler = await inject_request_id(app, index)
    handler = await access_log_middleware(app, handler)
    response = await handler(req)
    await echo_request_id(req, rep)

    assert response is rep
    assert rep.headers.get('x-request-id') == '123'
    event_log.info.assert_called_once_with(
        'http.access',
        path='/',
        outcome=200,
        duration=1.0,
        request='123',
    )


@pytest.mark.parametrize('status', [
    201,
    204,
    302,
])
@pytest.mark.asyncio
async def test_middleware_success_other(event_loop, status):
    event_log = mock.MagicMock()
    clock = mock.MagicMock()
    clock.side_effect = [0.0, 1.0]
    app = {
        'gitmesh.event_log': event_log,
        'gitmesh.clock': clock,
    }

    def mock_get(k, d):
        assert k.lower() == 'x-request-id'
        assert d == '?'
        return '123'

    req = mock.MagicMock(autospec=web.Request)
    req.path = '/'
    req.get.side_effect = mock_get
    rep = web.Response(body=b'...', status=status)

    async def index(request):
        assert request is req
        return rep

    handler = await access_log_middleware(app, index)
    response = await handler(req)
    await echo_request_id(req, rep)

    assert response is rep
    assert rep.headers.get('x-request-id') == '123'
    event_log.info.assert_called_once_with(
        'http.access',
        path='/',
        outcome=status,
        duration=1.0,
        request='123',
    )


@pytest.mark.parametrize('exc_class,expected_status', [
    (web.HTTPBadRequest, 400),
    (web.HTTPNotFound, 404),
    (web.HTTPConflict, 409),
])
@pytest.mark.asyncio
async def test_middleware_failure_http_exception(exc_class, expected_status):
    event_log = mock.MagicMock()
    clock = mock.MagicMock()
    clock.side_effect = [0.0, 1.0]
    app = {
        'gitmesh.event_log': event_log,
        'gitmesh.clock': clock,
    }

    def mock_get(k, d):
        assert k.lower() == 'x-request-id'
        assert d == '?'
        return '123'

    req = mock.MagicMock()
    req.path = '/'
    req.get.side_effect = mock_get

    async def index(request):
        assert request is req
        raise exc_class

    handler = await access_log_middleware(app, index)
    with pytest.raises(exc_class) as exc:
        print(await handler(req))
    rep = exc.value
    await echo_request_id(req, rep)

    assert rep.headers.get('x-request-id') == '123'

    event_log.info.assert_called_once_with(
        'http.access',
        path='/',
        outcome=expected_status,
        duration=1.0,
        request='123',
    )


@pytest.mark.parametrize('exc_class', [
    ValueError,
    OSError,
    KeyError,
])
@pytest.mark.asyncio
async def test_middleware_failure_other_exception(exc_class):
    event_log = mock.MagicMock()
    clock = mock.MagicMock()
    clock.side_effect = [0.0, 1.0]
    app = {
        'gitmesh.event_log': event_log,
        'gitmesh.clock': clock,
    }

    def mock_get(k, d):
        assert k.lower() == 'x-request-id'
        assert d == '?'
        return '123'

    req = mock.MagicMock(autospec=web.Request)
    req.path = '/'
    req.get.side_effect = mock_get

    async def index(request):
        assert request is req
        raise exc_class

    handler = await access_log_middleware(app, index)
    with pytest.raises(exc_class):
        print(await handler(req))
    rep = web.HTTPInternalServerError()
    await echo_request_id(req, rep)

    assert rep.headers.get('x-request-id') == '123'

    event_log.info.assert_called_once_with(
        'http.access',
        path='/',
        outcome=500,
        duration=1.0,
        request='123',
    )
