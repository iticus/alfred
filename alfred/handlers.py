"""
Created on Dec 17, 2017

@author: ionut
"""

import json
import logging
import tornado.web
import tornado.websocket
import utils


class BaseHandler(tornado.web.RequestHandler):
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

    @tornado.gen.coroutine
    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")
        user = yield self.db_client.get_user(username)
        if not user or not utils.compare_pwhashes(user["password"],
                                                  password, self.config.PW_ITERATIONS):
            error_msg = "?error=" + tornado.escape.url_escape("login incorrect")
            return self.redirect("/login/" + error_msg)

        self.set_current_user(user)
        return self.redirect(self.get_argument("next", "/"))

    def set_current_user(self, user):
        """
        Set cookie if user is user is set
        :param user: user data
        """
        if user:
            self.set_secure_cookie("username", tornado.escape.json_encode(user["username"]))
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

    @tornado.web.authenticated
    def get(self):
        self.render("home.html", vapid_public_key=self.config.VAPID_PUBLIC_KEY)


class SensorsHandler(BaseHandler):
    """Request Handler for "/sensors"
    Available methods: GET
    """

    @tornado.web.authenticated
    @tornado.gen.coroutine
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

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        """Return all switches data"""
        switches = yield self.db_client.get_switch_signals()
        for switch in switches:
            switch["value"] = self.application.cache.get(switch["id"], None)
        self.finish({"status": "OK", "switches": switches})

    @tornado.web.authenticated
    @tornado.gen.coroutine
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

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        """Return all sound data"""
        sounds = yield self.db_client.get_sound_signals()
        self.finish({"status": "OK", "sounds": sounds})

    @tornado.web.authenticated
    @tornado.gen.coroutine
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

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        """Return all available cameras"""
        cameras = yield self.db_client.get_camera_signals()
        return self.finish({"status": "OK", "cameras": cameras})


class VideoHandler(tornado.websocket.WebSocketHandler):
    """
    Request Handler for "/video/"
    """

    def select_subprotocol(self, subprotocols):
        logging.info("got subprotocols %s", subprotocols)
        subprotocol = subprotocols[0] if subprotocols else None
        return subprotocol

    def open(self):
        logging.info("new ws client %s", self)
        if not self.get_secure_cookie("username"):
            logging.warning("received non-aunthenticated ws connection")
            return self.close()
        url = self.get_argument("url", None)
        if not url:
            return self.close()
        return self.loop(url)

    def on_close(self):
        logging.info("removing ws client %s", self)

    def on_message(self, message):
        logging.info("got ws message %s from %s", message, self)

    @tornado.gen.coroutine
    def loop(self, url):
        """
        Open a new websocket connection and relay data to client
        :param url: target websocket connection
        """
        conn = yield tornado.websocket.websocket_connect(url)
        while True:
            message = yield conn.read_message()
            if not message:
                break
            try:
                self.write_message(message, binary=True)
            except tornado.websocket.WebSocketClosedError:
                break
        conn.close()


class SubscribeHandler(BaseHandler):
    """Request Handler for "/subscribe" - handle push subscribe requests
    Available methods: POST
    """

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self):
        """Add new subscription info"""
        subscription = json.loads(self.request.body.decode())
        result = yield self.db_client.add_subscription(subscription)
        if not result:
            return self.finish({"status": "error"})
        return self.finish({"status": "OK"})
