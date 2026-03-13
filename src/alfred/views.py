"""
Created on Dec 17, 2017

@author: ionut
"""

import logging
from typing import Any, Callable

import aiohttp.client
import aiohttp_jinja2
from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from aiohttp_session import get_session, new_session

from alfred import appkeys
from alfred import utils


class BaseView(web.View):
    """Base View to be inherited / implemented by subsequent views"""

    def __init__(self, request: web.Request) -> None:
        super().__init__(request)
        self.config = self.request.app[appkeys.config]
        self.database = self.request.app[appkeys.database]
        self.cache = self.request.app[appkeys.cache]

    @staticmethod
    def authenticated(func: Callable) -> Callable:
        """
        Decorator for checking authentication for requests
        :param func: function to decorate
        :return: decorator
        """

        async def wrapper(self: web.Request, *args: Any, **kwargs: Any) -> Any:
            self.session = await get_session(self.request)
            if "username" not in self.session:
                next_url = self.request.rel_url or "/"
                return web.HTTPFound(f"/login?next={next_url}")
            return await func(self, *args, **kwargs)

        return wrapper


class Login(BaseView):
    """Handle login page and POST request"""

    async def get(self) -> web.Response:
        message = self.request.query.get("message")
        next_url = self.request.query.get("next", "/")
        context = {"message": message, "next_url": next_url}
        return aiohttp_jinja2.render_template("login.html", self.request, context=context)

    async def post(self) -> web.Response:
        data = await self.request.post()
        if data.get("username") and data.get("password"):
            user = await self.database.get_user(data["username"])
            if not user:
                return web.HTTPFound(location="/login?message=no such user found")
            if not utils.compare_pwhash(user["password"], data["password"]):
                return web.HTTPFound(location="/login?message=invalid password")
        else:
            return web.HTTPFound(location="/login?message=provide username and password")
        session = await new_session(self.request)
        session["username"] = user["username"]
        next_url = self.request.query.get("next", "/")
        return web.HTTPFound(next_url)


class Logout(BaseView):
    """Logout user"""

    @BaseView.authenticated
    async def post(self) -> web.Response:
        session = await get_session(self.request)
        session.invalidate()
        return web.HTTPFound(location="/")


class Home(BaseView):
    """Request Handler for "/", render home template"""

    @BaseView.authenticated
    async def get(self):
        context = {
            "vapid_public_key": self.config.VAPID_PUBLIC_KEY,
            "session": self.session,
        }
        return aiohttp_jinja2.render_template("home.html", self.request, context=context)


class Sensors(BaseView):
    """Request Handler for "/sensors"
    Available methods: GET
    """

    @BaseView.authenticated
    async def get(self):
        """Return all switches data"""
        sensors = await self.database.get_sensor_signals()
        for sensor in sensors:
            sensor["value"] = self.cache.get(sensor["id"], None)
        return web.json_response({"status": "ok", "sensors": sensors})


class Switches(BaseView):
    """Request Handler for "/switches"
    Available methods: GET, POST
    """

    @BaseView.authenticated
    async def get(self):
        """Return all switches data"""
        switches = await self.database.get_switch_signals()
        for switch in switches:
            switch["value"] = self.cache.get(switch["id"], None)
        return web.json_response({"status": "ok", "switches": switches})

    @BaseView.authenticated
    async def post(self):
        """Toggle switch"""
        data = await self.post()
        sid = int(data.get("sid", "0"))
        signals = await self.database.get_switch_signals(sid)
        signal = signals[0]
        state = data.get("state")
        response = await utils.control_switch(signal, state)
        if "ok" not in response.lower():
            return web.json_response({"status": "error"}, status=500)
        self.cache[sid] = True if state == "1" else False
        return web.json_response({"status": "ok"})


class Sounds(BaseView):
    """Request Handler for "/sounds"
    Available methods: GET, POST
    """

    @BaseView.authenticated
    async def get(self):
        """Return all sound data"""
        sounds = await self.database.get_sound_signals()
        return web.json_response({"status": "ok", "sounds": sounds})

    @BaseView.authenticated
    async def post(self):
        """Play sound"""
        url = self.request.query.get("url")
        response = await utils.play_sound(url)
        if response != "ok":
            return web.json_response({"status": "error"}, status=500)
        return web.json_response({"status": "ok"})


class Cameras(BaseView):
    """Request Handler for "/cameras/"
    Available methods: GET
    """

    @BaseView.authenticated
    async def get(self):
        """Return all available cameras"""
        cameras = await self.database.get_camera_signals()
        return web.json_response({"status": "ok", "cameras": cameras})


class VideoHTTP(BaseView):
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
        self.client = aiohttp.client.ClientSession()

    def on_close(self):
        logging.info("removing ws http_video client %s", self)

    async def on_message(self, message):
        try:
            if message == "?":
                image = await self.client.get(self.url)
                self.write_message(image.body, binary=True)
            elif message == "!":
                logging.info("closing websocket by client request")
                self.close()
            else:
                self.write_message(message)  # echo
        except Exception as exc:
            logging.error("cannot handle mjpeg data %s", exc)
            self.close()


class VideoWS(BaseView):
    """
    Request Handler for "/ws_video/"
    """

    def select_subprotocol(self, subprotocols):
        logging.info("got subprotocols %s", subprotocols)
        subprotocol = subprotocols[0] if subprotocols else None
        return subprotocol

    async def open(self):
        logging.info("new ws_video client %s", self)
        if not self.get_secure_cookie("username"):
            logging.warning("received non-aunthenticated ws connection")
            return self.close()
        url = self.get_argument("url", None)
        if not url:
            return self.close()
        self.upstream = await websocket_connect(url, on_message_callback=self.upstream_message)

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


class Subscribe(BaseView):
    """Request Handler for "/subscribe" - handle push subscribe requests
    Available methods: POST
    """

    @BaseView.authenticated
    async def post(self):
        """Add new subscription info"""
        subscription = await self.post()
        result = await self.database.add_subscription(subscription)
        if not result:
            return web.json_response({"status": "error"}, status=500)
        return web.json_response({"status": "ok"})


class ServiceWorker(web.View):
    """Render static service worker file"""

    async def get(self) -> web.FileResponse:
        return FileResponse("static/service-worker.js")


class Favicon(web.View):
    """Render static favicon file"""

    async def get(self) -> web.FileResponse:
        return FileResponse("static/favicon.png")
