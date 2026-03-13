"""
Created on 2026-03-13

@author: iticus
"""

import logging
from typing import Callable

import aiohttp_jinja2
from aiohttp import web, web_exceptions

logger = logging.getLogger(__name__)


@web.middleware
async def error_middleware(request: web.Request, handler: Callable) -> web.Response:
    """
    Try to handle the request and render a custom error page if an exception occurs
    :param request: web Request to handle
    :param handler: handler to execute
    :return: web response object
    """
    try:
        response = await handler(request)
        if response.status != 500:
            return response
        message = response.message
    except web_exceptions.HTTPNotFound:
        logger.warning("cannot find page %s, 404", request.path)
        message = "requested page not found"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        message = str(exc)
        logger.exception("cannot process page: %s", request.path)
    return aiohttp_jinja2.render_template("error.html", request, context={"message": message}, status=500)
