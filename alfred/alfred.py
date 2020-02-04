"""
Created on Dec 17, 2017

@author: ionut
"""

import datetime
import functools
import logging
import signal
import sys
import tornado.ioloop
import tornado.web
from tornado.gen import WaitIterator

import handlers
import settings
from database import DBClient
from utils import format_frame, control, send_push_notification


def app_exit():
    """Stop IOLoop and exit"""
    tornado.ioloop.IOLoop.instance().stop()
    logging.info("finished")


def cleanup_hook(exc_type, exc_value, exc_traceback):
    """Log exception details and call app_exit"""
    logging.error("Uncaught exception, stopping", exc_info=(exc_type, exc_value, exc_traceback))
    app_exit()


def configure_signals():
    """Configure signal handling to cleanly exit the application"""

    def stopping_handler(signum, frame):
        """Log frame details and call app_exit"""
        frame_data = format_frame(frame)
        logging.info("interrupt signal %s, frame %s received, stopping", signum, frame_data)
        app_exit()

    signal.signal(signal.SIGINT, stopping_handler)
    signal.signal(signal.SIGTERM, stopping_handler)


@tornado.gen.coroutine
def run_control(app):
    """
    Run control function to retrive signal values and process schedules
    :param app: tornado application instance
    """
    try:
        yield control(app)
    except Exception as exc:
        payload = "cannot run control code: %s" % exc
        logging.error(payload)
        subscriptions = yield app.database.get_subscriptions()
        sub_dict = {}
        for subscription in subscriptions:
            key = "%s" % subscription["id"]
            sub_dict[key] = send_push_notification(payload, app.config, subscription)
        wait_iterator = WaitIterator(**sub_dict)
        while not wait_iterator.done():
            try:
                result = yield wait_iterator.next()
                if result:
                    logging.info("subscription %s, result %s", wait_iterator.current_index, result)
            except Exception as exc:
                logging.error("subscription %s, exception %s", wait_iterator.current_index, exc)

    tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=30),
                                                 functools.partial(run_control, app))


def make_app(io_loop=None):
    """
    Create and return tornado.web.Application object so it can be used in tests too
    :param io_loop: already existing io_loop (used for testing)
    :returns: application instance
    """
    app = tornado.web.Application(
        [
            (r"/", handlers.HomeHandler),
            (r"/login/?", handlers.LoginHandler),
            (r"/logout/?", handlers.LogoutHandler),
            (r"/sensors/?", handlers.SensorsHandler),
            (r"/switches/?", handlers.SwitchesHandler),
            (r"/sounds/?", handlers.SoundsHandler),
            (r"/cameras/?", handlers.CamerasHandler),
            (r"/http_video/?", handlers.VideoHTTPHandler),
            (r"/ws_video/?", handlers.VideoWSHandler),
            (r"/subscribe/?", handlers.SubscribeHandler),
            (r"/(manifest\.json)", tornado.web.StaticFileHandler, {"path": "static"}),
            (r"/(service\-worker\.js)", tornado.web.StaticFileHandler, {"path": "static"}),
        ],
        template_path=settings.TEMPLATE_PATH,
        static_path=settings.STATIC_PATH,
        cookie_secret=settings.COOKIE_SECRET,
        login_url="/login/",
        xsrf_cookies=True
    )
    app.config = settings
    app.database = DBClient(settings.DSN, io_loop)
    app.cache = {}
    app.io_loop = io_loop
    return app


def main():
    """Start Tornado application instance"""
    application = make_app()
    logging.info("starting alfred on %s:%s", application.config.ADDRESS, application.config.PORT)
    application.listen(application.config.PORT, address=application.config.ADDRESS)
    run_control(application)
    if application.io_loop:
        application.io_loop.start()
    else:
        tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    sys.excepthook = cleanup_hook
    configure_signals()
    main()
