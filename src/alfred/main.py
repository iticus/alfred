"""
Created on Dec 17, 2017

@author: ionut
"""

import asyncio
import datetime
import functools
import logging
from pathlib import Path

import aiohttp_jinja2
import jinja2
import redis.asyncio as redis
from aiohttp_session import setup
from aiohttp_session.redis_storage import RedisStorage
from aiohttp import web

from alfred import appkeys
from alfred import views
from alfred import settings
from alfred.database import DBClient
from alfred.middlewares import error_middleware
from alfred.utils import control, send_push_notification

logger = logging.getLogger(__name__)


async def startup(app: web.Application) -> None:
    """
    Establish database and cache connections
    :param app: application instance
    """
    logger.info("connecting to database")
    await app[appkeys.database].connect()
    # await app.database.create_structure()
    logger.info("connecting to REDIS instance")
    app[appkeys.cache] = redis.Redis(
        host=app[appkeys.config].REDIS_HOST,
        port=app[appkeys.config].REDIS_PORT,
        password=app[appkeys.config].REDIS_PASSWORD,
    )
    await app[appkeys.cache].ping()
    storage = RedisStorage(app[appkeys.cache], max_age=14 * 86400)
    setup(app, storage)


async def shutdown(app: web.Application) -> None:
    """
    Gracefully disconnect from database and cache servers
    :param app: application instance
    """
    logger.info("disconnecting from database")
    await app[appkeys.database].disconnect()
    logger.info("disconnecting from redis")
    await app[appkeys.cache].aclose()
    await asyncio.sleep(0.1)


async def run_control(app: web.Application):
    """
    Run control function to retrieve signal values and process schedules
    :param app: tornado application instance
    """
    now = datetime.datetime.now()
    one_day = datetime.timedelta(hours=24)
    try:
        await control(app)
    except Exception as exc:
        payload = "cannot run control code: %s" % exc
        logging.error(payload)
        subscriptions = await app.database.get_subscriptions()
        sub_dict = {}
        for subscription in subscriptions:
            key = "%s" % subscription["id"]
            if key in app.cache["NOTIFICATION_CACHE"] and now - app.cache["NOTIFICATION_CACHE"][key] < one_day:
                continue
            sub_dict[key] = send_push_notification(payload, app.config, subscription)
            app.cache["NOTIFICATION_CACHE"][key] = now
        if sub_dict:
            wait_iterator = WaitIterator(**sub_dict)
            while not wait_iterator.done():
                try:
                    result = await wait_iterator.next()
                    if result:
                        logging.info(
                            "subscription %s, result %s",
                            wait_iterator.current_index,
                            result,
                        )
                except Exception as exc:
                    logging.error(
                        "subscription %s, exception %s",
                        wait_iterator.current_index,
                        exc,
                    )
    td = datetime.timedelta(seconds=30)
    tornado.ioloop.IOLoop.instance().add_timeout(td, functools.partial(run_control, app))


def make_app():
    """
    Create and return tornado.web.Application object so it can be used in tests too
    :param io_loop: already existing io_loop (used for testing)
    :returns: application instance
    """
    app = web.Application()
    (app.router.add_view("/", views.Home),)
    app.router.add_view(r"/login{tail:.*?}", views.Login)
    app.router.add_view(r"/logout{tail:.*?}", views.Logout)
    app.router.add_view(r"/sensors{tail:.*?}", views.Sensors)
    app.router.add_view(r"/switches{tail:.*?}", views.Switches)
    app.router.add_view(r"/sounds{tail:.*?}", views.Sounds)
    app.router.add_view(r"/cameras{tail:.*?}", views.Cameras)
    app.router.add_view(r"/http_video{tail:.*?}", views.VideoHTTP)
    app.router.add_view(r"/ws_video{tail:.*?}", views.VideoWS)
    app.router.add_view(r"/subscribe{tail:.*?}", views.Subscribe)
    app.router.add_static("/static", Path(__file__).parent / "static")
    app.router.add_view("/favicon.ico", views.Favicon)
    app.router.add_view("/service-worker.js", views.ServiceWorker)
    app.middlewares.append(error_middleware)
    app[appkeys.config] = settings
    app[appkeys.database] = DBClient(settings.DSN)
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates"))
    app.on_startup.append(startup)
    app.on_shutdown.append(shutdown)

    return app


def main() -> None:
    """Start main web application instance"""
    application = make_app()
    loop = asyncio.new_event_loop()
    # loop.create_task(run_control(application))
    logging.info(
        "starting alfred on %s:%s",
        application[appkeys.config].ADDRESS,
        application[appkeys.config].PORT,
    )
    web.run_app(
        application,
        host=application[appkeys.config].ADDRESS,
        port=application[appkeys.config].PORT,
        access_log=None,
    )


if __name__ == "__main__":
    main()
