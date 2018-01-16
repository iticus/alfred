"""
Created on Dec 17, 2017

@author: ionut
"""

import datetime
import functools
import importlib
import logging
import signal
import sys
import tornado.ioloop
import tornado.web

import handlers
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
        results = []
        try:
            subscriptions = yield app.database.get_subscriptions()
            for subscription in subscriptions:
                results.append(send_push_notification(payload, app.config, subscription))
            yield results
        except Exception as exc:
            logging.error("cannot push notification, %s", exc)

    tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=30),
                                                 functools.partial(run_control, app))


def make_app(settings_module=None, ioloop=None):
    """
    Create and return tornado.web.Application object so it can be used in tests too
    :param settings_module: custom settings_module (production / development)
    :param ioloop: already existing ioloop (used for testing)
    :returns: application instance
    """
    if settings_module:
        settings_module = importlib.import_module("settings.%s" % settings_module)
    else:
        settings_module = importlib.import_module("settings.production")
    app = tornado.web.Application(
        [
            (r"/", handlers.HomeHandler),
            (r"/login/?", handlers.LoginHandler),
            (r"/logout/?", handlers.LogoutHandler),
            (r"/sensors/?", handlers.SensorsHandler),
            (r"/switches/?", handlers.SwitchesHandler),
            (r"/cameras/?", handlers.CamerasHandler),
            (r"/subscribe/?", handlers.SubscribeHandler),
            (r"/(manifest\.json)", tornado.web.StaticFileHandler, {"path": "static"}),
            (r"/(service\-worker\.js)", tornado.web.StaticFileHandler, {"path": "static"}),
        ],
        template_path=settings_module.TEMPLATE_PATH,
        static_path=settings_module.STATIC_PATH,
        cookie_secret=settings_module.COOKIE_SECRET,
        login_url="/login/",
        xsrf_cookies=True
    )
    app.config = settings_module
    app.database = DBClient(settings_module.DSN, ioloop)
    app.cache = {}
    app.ioloop = ioloop
    return app


def main():
    """Start Tornado application instance"""
    application = make_app()
    logging.info("starting alfred on %s:%s", application.config.ADDRESS, application.config.PORT)
    application.listen(application.config.PORT, address=application.config.ADDRESS)
    run_control(application)
    if application.ioloop:
        application.ioloop.start()
    else:
        tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    sys.excepthook = cleanup_hook
    configure_signals()
    main()
