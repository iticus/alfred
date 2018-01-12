"""
Created on Dec 17, 2017

@author: ionut
"""

import json
import tornado.web
from tornado.httpclient import AsyncHTTPClient
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
        self.render("login.html", error_message=error_message)


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
        self.redirect(self.get_argument("next", "/"))


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
        url = self.get_argument("url")
        state = self.get_argument("state")
        response = yield utils.control_switch(url, state)
        if response != "OK":
            return self.finish({"status": "error"})
        self.application.cache[sid] = True if state == "1" else False
        self.finish({"status": "OK"})


class CamerasHandler(BaseHandler):
    """Request Handler for "/cameras/"
    Available methods: GET
    """


    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        """Return all available cameras or single camera data"""
        sid = self.get_argument("sid", None)
        url = self.get_argument("url", None)
        if not sid or not url:
            cameras = yield self.db_client.get_camera_signals()
            return self.finish({"status": "OK", "cameras": cameras})

        sid = int(sid)
        url = url + "/?action=snapshot"
        client = AsyncHTTPClient()
        response = yield client.fetch(url)
        self.finish(response.body)


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
        self.finish({"status": "OK"})
