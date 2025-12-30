from contextlib import asynccontextmanager

import pytest
from pytest_mock import MockerFixture

from mrok.proxy.asgi import ASGIAppWrapper
from mrok.types.proxy import Message
from tests.types import ReceiveFactory, SendFactory


def test_wrapper_middleware_stack(mocker: MockerFixture):
    m_app = mocker.MagicMock()

    m_mw1 = mocker.MagicMock()
    m_mw1_ctor = mocker.MagicMock(return_value=m_mw1)
    args1 = ("a", True)
    kwargs1 = {"mykwargs1": "value1"}

    m_mw2 = mocker.MagicMock()
    m_mw2_ctor = mocker.MagicMock(return_value=m_mw2)
    args2 = ("b", False)
    kwargs2 = {"mykwargs2": "value2"}

    wrapper = ASGIAppWrapper(m_app)
    wrapper.add_middleware(m_mw1_ctor, *args1, **kwargs1)  # type: ignore
    wrapper.add_middleware(m_mw2_ctor, *args2, **kwargs2)  # type: ignore

    stack = wrapper.build_middleware_stack()
    assert stack == m_mw2

    m_mw1_ctor.assert_called_once_with(m_app, *args1, **kwargs1)
    m_mw2_ctor.assert_called_once_with(m_mw1, *args2, **kwargs2)


async def test_wrapper_lifespan_stack(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
):
    m_inner_startup = mocker.AsyncMock()
    m_inner_shutdown = mocker.AsyncMock()

    @asynccontextmanager
    async def inner_lifespan(app):
        await m_inner_startup()
        yield
        await m_inner_shutdown()

    m_outer_startup = mocker.AsyncMock()
    m_outer_shutdown = mocker.AsyncMock()

    @asynccontextmanager
    async def outer_lifespan(app):
        await m_outer_startup()
        yield {"outer_state": "a state"}
        await m_outer_shutdown()

    m_wrapper_router = mocker.AsyncMock(lifespan_context=inner_lifespan)
    m_wrapped_app = mocker.AsyncMock(router=m_wrapper_router)

    sent: list[Message] = []
    receive = receive_factory([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])
    send = send_factory(sent)

    wrapper = ASGIAppWrapper(
        m_wrapped_app,
        lifespan=outer_lifespan,
    )

    await wrapper({"type": "lifespan", "state": {}}, receive, send)
    assert sent == [
        {"type": "lifespan.startup.complete"},
        {"type": "lifespan.shutdown.complete"},
    ]
    m_inner_startup.assert_awaited_once()
    m_inner_shutdown.assert_awaited_once()
    m_outer_startup.assert_awaited_once()
    m_outer_shutdown.assert_awaited_once()


async def test_wrapper_no_app_lifespan(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
):
    m_outer_startup = mocker.AsyncMock()
    m_outer_shutdown = mocker.AsyncMock()

    @asynccontextmanager
    async def outer_lifespan(app):
        await m_outer_startup()
        yield {"outer_state": "a state"}
        await m_outer_shutdown()

    m_wrapper_router = mocker.AsyncMock(lifespan_context=None)
    m_wrapped_app = mocker.AsyncMock(router=m_wrapper_router)

    sent: list[Message] = []
    receive = receive_factory([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])
    send = send_factory(sent)

    wrapper = ASGIAppWrapper(
        m_wrapped_app,
        lifespan=outer_lifespan,
    )

    await wrapper({"type": "lifespan", "state": {}}, receive, send)
    assert sent == [
        {"type": "lifespan.startup.complete"},
        {"type": "lifespan.shutdown.complete"},
    ]
    m_outer_startup.assert_awaited_once()
    m_outer_shutdown.assert_awaited_once()


async def test_wrapper_no_starlette_app(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
):
    m_outer_startup = mocker.AsyncMock()
    m_outer_shutdown = mocker.AsyncMock()

    @asynccontextmanager
    async def outer_lifespan(app):
        await m_outer_startup()
        yield {"outer_state": "a state"}
        await m_outer_shutdown()

    m_wrapped_app = mocker.AsyncMock(router=None)

    sent: list[Message] = []
    receive = receive_factory([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])
    send = send_factory(sent)

    wrapper = ASGIAppWrapper(
        m_wrapped_app,
        lifespan=outer_lifespan,
    )

    await wrapper({"type": "lifespan", "state": {}}, receive, send)
    assert sent == [
        {"type": "lifespan.startup.complete"},
        {"type": "lifespan.shutdown.complete"},
    ]
    m_outer_startup.assert_awaited_once()
    m_outer_shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_wrapper_no_lifespan(
    mocker: MockerFixture,
):
    m_app = mocker.AsyncMock(router=None)

    m_receive = mocker.AsyncMock()
    m_send = mocker.AsyncMock()

    wrapper = ASGIAppWrapper(m_app)

    await wrapper({"type": "lifespan"}, m_receive, m_send)
    m_app.assert_not_awaited()


@pytest.mark.asyncio
async def test_wrapper_invoke_app(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
):
    m_app = mocker.AsyncMock()

    receive = receive_factory()
    m_send = mocker.AsyncMock()

    wrapper = ASGIAppWrapper(m_app)

    await wrapper({"type": "http"}, receive, m_send)
    m_app.assert_awaited_once_with({"type": "http"}, receive, m_send)


async def test_wrapper_lifespan_state_unsupported(
    mocker: MockerFixture,
    receive_factory: ReceiveFactory,
    send_factory: SendFactory,
):
    m_outer_startup = mocker.AsyncMock()
    m_outer_shutdown = mocker.AsyncMock()

    @asynccontextmanager
    async def outer_lifespan(app):
        await m_outer_startup()
        yield {"outer_state": "a state"}
        await m_outer_shutdown()

    m_wrapped_app = mocker.AsyncMock(router=None)

    sent: list[Message] = []
    receive = receive_factory([{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])
    send = send_factory(sent)

    wrapper = ASGIAppWrapper(
        m_wrapped_app,
        lifespan=outer_lifespan,
    )
    with pytest.raises(Exception) as cv:
        await wrapper({"type": "lifespan"}, receive, send)

    assert str(cv.value) == '"state" is unsupported by the current ASGI Server.'
