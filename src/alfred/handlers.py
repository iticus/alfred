"""
Created on Dec 17, 2017

@author: ionut
"""

import json
import logging
from tornado.escape import url_escape, json_encode
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient
from tornado.web import authenticated, RequestHandler
from tornado.websocket import websocket_connect, WebSocketHandler, WebSocketClosedError

import utils


class BaseHandler(RequestHandler):
    """Base Handler to be inherited / implemented by subsequent handlers"""

    def get_current_user(self):
        return self.get_secure_cookie("username")

    def initialize(self):
        self.config = self.application.config
        self.db_client = self.application.database


class LoginHandler(BaseHandler):
    """Request Handler for "/login", checks login details and sets cookie"""

    def get(self):
        if self.get_secure_cookie("username"):
            return self.redirect(self.get_argument("next", "/"))

        error_message = self.get_argument("error", "")
        return self.render("login.html", error_message=error_message)

    @coroutine
    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")
        user = yield self.db_client.get_user(username)
        if not user or not utils.compare_pwhashes(user["password"],
                                                  password, self.config.PW_ITERATIONS):
            error_msg = "?error=" + url_escape("login incorrect")
            return self.redirect("/login/" + error_msg)

        self.set_current_user(user)
        return self.redirect(self.get_argument("next", "/"))

    def set_current_user(self, user):
        """
        Set cookie if user is user is set
        :param user: user data
        """
        if user:
            self.set_secure_cookie("username", json_encode(user["username"]))
        else:
            self.clear_cookie("username")


class LogoutHandler(BaseHandler):
    """Request Handler for "/logout", clears cookie"""

    def get(self):
        return self.redirect("/")

    def post(self):
        self.clear_cookie("username")
        self.redirect(self.get_argument("next", "/"))


class HomeHandler(BaseHandler):
    """Request Handler for "/", render home template"""

    @authenticated
    def get(self):
        self.render("home.html", vapid_public_key=self.config.VAPID_PUBLIC_KEY)


class SensorsHandler(BaseHandler):
    """Request Handler for "/sensors"
    Available methods: GET
    """

    @authenticated
    @coroutine
    def get(self):
        """Return all switches data"""
        sensors = yield self.db_client.get_sensor_signals()
        for sensor in sensors:
            sensor["value"] = self.application.cache.get(sensor["id"], None)
        self.finish({"status": "OK", "sensors": sensors})


class SwitchesHandler(BaseHandler):
    """Request Handler for "/switches"
    Available methods: GET, POST
    """

    @authenticated
    @coroutine
    def get(self):
        """Return all switches data"""
        switches = yield self.db_client.get_switch_signals()
        for switch in switches:
            switch["value"] = self.application.cache.get(switch["id"], None)
        self.finish({"status": "OK", "switches": switches})

    @authenticated
    @coroutine
    def post(self):
        """Toggle switch"""
        sid = int(self.get_argument("sid"))
        signals = yield self.db_client.get_switch_signals(sid)
        signal = signals[0]
        state = self.get_argument("state")
        response = yield utils.control_switch(signal, state)
        if "ok" not in response.lower():
            return self.finish({"status": "error"})
        self.application.cache[sid] = True if state == "1" else False
        return self.finish({"status": "OK"})


class SoundsHandler(BaseHandler):
    """Request Handler for "/sounds"
    Available methods: GET, POST
    """

    @authenticated
    @coroutine
    def get(self):
        """Return all sound data"""
        sounds = yield self.db_client.get_sound_signals()
        self.finish({"status": "OK", "sounds": sounds})

    @authenticated
    @coroutine
    def post(self):
        """Play sound"""
        url = self.get_argument("url")
        response = yield utils.play_sound(url)
        if response != "OK":
            return self.finish({"status": "error"})
        return self.finish({"status": "OK"})


class CamerasHandler(BaseHandler):
    """Request Handler for "/cameras/"
    Available methods: GET
    """

    @authenticated
    @coroutine
    def get(self):
        """Return all available cameras"""
        cameras = yield self.db_client.get_camera_signals()
        return self.finish({"status": "OK", "cameras": cameras})


class VideoHTTPHandler(WebSocketHandler):
    """
    Request Handler for "/http_video/"
    """

    def open(self):
        logging.info("new ws http_video client %s", self)
        if not self.get_secure_cookie("username"):
            logging.warning("received non-aunthenticated ws connection")
            return self.close()
        self.url = self.get_argument("url", None)
        if not self.url:
            return self.close()
        self.client = AsyncHTTPClient()

    def on_close(self):
        logging.info("removing ws http_video client %s", self)

    @coroutine
    def on_message(self, message):
        try:
            if message == "?":
                image = yield self.client.fetch(self.url)
                self.write_message(image.body, binary=True)
            elif message == "!":
                logging.info("closing websocket by client request")
                self.close()
            else:
                self.write_message(message)  # echo
        except Exception as exc:
            logging.error("cannot handle mjpeg data %s", exc)
            self.close()


class VideoWSHandler(WebSocketHandler):
    """
    Request Handler for "/ws_video/"
    """

    def select_subprotocol(self, subprotocols):
        logging.info("got subprotocols %s", subprotocols)
        subprotocol = subprotocols[0] if subprotocols else None
        return subprotocol

    @coroutine
    def open(self):
        logging.info("new ws_video client %s", self)
        if not self.get_secure_cookie("username"):
            logging.warning("received non-aunthenticated ws connection")
            return self.close()
        url = self.get_argument("url", None)
        if not url:
            return self.close()
        self.upstream = yield websocket_connect(url, on_message_callback=self.upstream_message)

    def on_close(self):
        self.upstream.close()
        logging.info("removing ws_video client %s", self)

    def on_message(self, message):
        if message == "!":
            logging.info("closing websocket by client request")
            self.close()
        elif message != "?":
            logging.info("got ws message %s from %s", message, self)

    def upstream_message(self, message):
        try:
            self.write_message(message, binary=True)
        except WebSocketClosedError:
            self.close()


class SubscribeHandler(BaseHandler):
    """Request Handler for "/subscribe" - handle push subscribe requests
    Available methods: POST
    """

    @authenticated
    @coroutine
    def post(self):
        """Add new subscription info"""
        subscription = json.loads(self.request.body.decode())
        result = yield self.db_client.add_subscription(subscription)
        if not result:
            return self.finish({"status": "error"})
        return self.finish({"status": "OK"})
