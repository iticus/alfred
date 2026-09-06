"""Created on 2026-03-13.

Copyright (C) 2026, Ionut Ticus (iticus), <ticus.ionut@gmail.com>
"""

import logging
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Callable

import aiohttp_jinja2
from aiohttp import web, web_exceptions
from aiohttp_session import get_session

logger = logging.getLogger(__name__)


@web.middleware
async def auth_middleware(request: web.Request, handler: Callable) -> web.Response:
    """Check authentication status and handle request.

    :param request: web Request to handle
    :param handler: handler to execute
    :return: web response object
    """
    if request.path.startswith("/login"):
        return await handler(request)
    request.session = await get_session(request)
    if "username" not in request.session:
        next_url = request.rel_url or "/"
        login_url = f"/login?next={next_url}"
        return web.HTTPFound(login_url)
    return await handler(request)


@web.middleware
async def error_middleware(request: web.Request, handler: Callable) -> web.Response:
    """Try to handle the request and render a custom error page if an exception occurs.

    :param request: web Request to handle
    :param handler: handler to execute
    :return: web response object
    """
    try:
        response = await handler(request)
        if response.status != web.HTTPInternalServerError.status_code:
            return response
        message = response.message
    except web_exceptions.HTTPNotFound:
        logger.warning("cannot find page %s, 404", request.path)
        message = "requested page not found"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        message = str(exc)
        logger.exception("cannot process page: %s", request.path)
    return aiohttp_jinja2.render_template("error.html", request, context={"message": message}, status=500)
