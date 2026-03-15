"""
Created on Dec 17, 2017

@author: ionut
"""

import asyncio
import datetime
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
    task = asyncio.create_task(run_control(app))
    logger.info("started  background task app %s", task)


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
    while True:
        now = datetime.datetime.now()
        one_day = datetime.timedelta(hours=24)
        try:
            logger.debug("running control loop")
            await control(app)
        except Exception as exc:
            logger.exception("cannot run control loop")
            subscriptions = await app[appkeys.database].get_subscriptions()
            tasks = {}
            payload = "cannot run control code: %s" % exc
            for subscription in subscriptions:
                key = f"{subscription['id']}"
                if (
                    key in app[appkeys.cache]["NOTIFICATION_CACHE"]
                    and now - app[appkeys.cache]["NOTIFICATION_CACHE"][key] < one_day
                ):
                    continue
                tasks[send_push_notification(payload, app[appkeys.config], subscription)] = key
                app[appkeys.cache]["NOTIFICATION_CACHE"][key] = now
            if not tasks:
                continue
            async for task in asyncio.as_completed(tasks.values()):
                try:
                    result = await task
                    if result:
                        logger.info("subscription %s, result %s", tasks[task], result)
                except Exception as exc:
                    logging.error("subscription %s, exception %s", tasks[task], exc)
        finally:
            await asyncio.sleep(30)


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
    app.router.add_view(r"/subscribe{tail:.*?}", views.Subscribe)
    app.router.add_static("/static", Path(__file__).parent / "static")
    app.router.add_view("/favicon.ico", views.Favicon)
    app.router.add_view("/service-worker.js", views.ServiceWorker)
    app.router.add_route("get", "/ws_video{tail:.*?}", views.websocket_handler)
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
