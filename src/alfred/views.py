"""Created on Dec 17, 2017.

Copyright (C) 2026, Ionut Ticus (iticus), <ticus.ionut@gmail.com>
"""

import logging
from typing import TYPE_CHECKING, Any

import aiohttp.client
import aiohttp_jinja2
from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from aiohttp_session import get_session, new_session

from alfred import appkeys, utils

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class BaseView(web.View):
    """Base View to be inherited / implemented by subsequent views."""

    def __init__(self, request: web.Request) -> None:
        """Create instance and assign DSN attribute.

        :param request: web request
        """
        super().__init__(request)
        self.config = self.request.app[appkeys.config]
        self.database = self.request.app[appkeys.database]
        self.cache = self.request.app[appkeys.cache]

    @staticmethod
    def authenticated(func: Callable) -> Callable:
        """Check authentication decorator.

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
    """Handle login page and POST request."""

    async def get(self) -> web.Response:
        """Render login page with optional error message."""
        message = self.request.query.get("message")
        next_url = self.request.query.get("next", "/")
        context = {"message": message, "next_url": next_url}
        return aiohttp_jinja2.render_template("login.html", self.request, context=context)

    async def post(self) -> web.Response:
        """Handle login request."""
        data = await self.request.post()
        if data.get("username") and data.get("password"):
            user = await self.database.get_user(data["username"])
            if not user:
                return web.HTTPFound(location="/login?message=no such user found")
            if not isinstance(data["password"], str) or not utils.compare_pwhash(user["password"], data["password"]):
                return web.HTTPFound(location="/login?message=invalid password")
        else:
            return web.HTTPFound(location="/login?message=provide username and password")
        session = await new_session(self.request)
        session["username"] = user["username"]
        next_url = self.request.query.get("next", "/")
        return web.HTTPFound(next_url)


class Logout(BaseView):
    """Logout user."""

    @BaseView.authenticated
    async def post(self) -> web.Response:
        """Handle logout request."""
        session = await get_session(self.request)
        session.invalidate()
        return web.HTTPFound(location="/")


class Home(BaseView):
    """Request Handler for "/", render home template."""

    @BaseView.authenticated
    async def get(self) -> web.Response:
        """Render home page."""
        context = {
            "vapid_public_key": self.config.VAPID_PUBLIC_KEY,
            "session": self.session,
        }
        return aiohttp_jinja2.render_template("home.html", self.request, context=context)


class Sensors(BaseView):
    """Request Handler for "/sensors".

    Available methods: GET
    """

    @BaseView.authenticated
    async def get(self) -> web.Response:
        """Return all sensor data."""
        sensors = await self.database.get_sensor_signals()
        for sensor in sensors:
            sensor["value"] = await self.cache.get(sensor["id"])
        return web.json_response({"status": "ok", "sensors": sensors})


class Switches(BaseView):
    """Request Handler for "/switches".

    Available methods: GET, POST
    """

    @BaseView.authenticated
    async def get(self) -> web.Response:
        """Return all switches data."""
        switches = await self.database.get_switch_signals()
        for switch in switches:
            switch["value"] = await self.cache.get(f"{switch['id']}")
        return web.json_response({"status": "ok", "switches": switches})

    @BaseView.authenticated
    async def post(self) -> web.Response:
        """Toggle switch."""
        data = await self.post()
        sid = data.get("sid", "0")
        signals = await self.database.get_switch_signals(int(sid))
        signal = signals[0]
        state = data.get("state")
        response = await utils.control_switch(signal, state)
        if "ok" not in response.lower():
            return web.json_response({"status": "error"}, status=500)
        await self.cache.set(sid, state)
        return web.json_response({"status": "ok"})


class Sounds(BaseView):
    """Request Handler for "/sounds".

    Available methods: GET, POST
    """

    @BaseView.authenticated
    async def get(self) -> web.Response:
        """Return all sound data."""
        sounds = await self.database.get_sound_signals()
        return web.json_response({"status": "ok", "sounds": sounds})

    @BaseView.authenticated
    async def post(self) -> web.Response:
        """Play sound."""
        url = self.request.query.get("url")
        if not url:
            return web.json_response({"status": "error", "message": "missing URL"}, status=400)
        response = await utils.play_sound(url)
        if response != "ok":
            return web.json_response({"status": "error"}, status=500)
        return web.json_response({"status": "ok"})


class Cameras(BaseView):
    """Request Handler for "/cameras/".

    Available methods: GET
    """

    @BaseView.authenticated
    async def get(self) -> web.Response:
        """Return all available cameras."""
        cameras = await self.database.get_camera_signals()
        return web.json_response({"status": "ok", "cameras": cameras})


class VideoHTTP(BaseView):
    """Request Handler for "/http_video/" ."""

    def open(self) -> None:
        """Handle new http video request."""
        logger.info("new http_video client %s", self)
        if not self.get_secure_cookie("username"):
            logger.warning("received non-aunthenticated connection")
            return self.close()
        self.url = self.request.get("url", None)
        if not self.url:
            return self.close()
        self.client = aiohttp.client.ClientSession()
        return None

    def on_close(self) -> None:
        """Handle http video closing."""
        logger.info("removing ws http_video client %s", self)

    async def on_message(self, message: str) -> None:
        """Handle message on websocket connection."""
        try:
            if message == "?":
                image = await self.client.get(self.url)
                self.write_message(image.body, binary=True)
            elif message == "!":
                logger.info("closing websocket by client request")
                self.close()
            else:
                self.write_message(message)  # echo
        except Exception:
            logger.exception("cannot handle mjpeg data")
            self.close()

async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Handle websocket connection.

    :param request: web request to handle
    """
    ws = web.WebSocketResponse()
    _ = await ws.prepare(request)
    url = request.query.get("url", None)
    if not url:
        return ws
    session = aiohttp.client.ClientSession()
    async with session.ws_connect(url) as wsc:
        async for msg in wsc:
            if msg.type == aiohttp.WSMsgType.BINARY:
                if msg.data == "close cmd":
                    await ws.close()
                    break
                await ws.send_str(msg.data + "/answer")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == "close":
                await ws.close()
            else:
                await ws.send_str(msg.data + "/answer")
        elif msg.type == aiohttp.WSMsgType.ERROR:
            logger.error("ws connection closed with exception %s", ws.exception())
    logger.info("websocket connection closed")
    return ws


'''
class VideoWS(BaseView):
    """
    Request Handler for "/ws_video/"
    """

    async def open(self):
        logging.info("new ws_video client %s", self)
        if not self.get_secure_cookie("username"):
            logging.warning("received non-aunthenticated ws connection")
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
'''

class Subscribe(BaseView):
    """Request Handler for "/subscribe" - handle push subscribe requests.

    Available methods: POST
    """

    @BaseView.authenticated
    async def post(self) -> web.Response:
        """Add new subscription info."""
        subscription = await self.post()
        result = await self.database.add_subscription(subscription)
        if not result:
            return web.json_response({"status": "error"}, status=500)
        return web.json_response({"status": "ok"})


class ServiceWorker(web.View):
    """Render static service worker file."""

    async def get(self) -> web.FileResponse:
        """Render static service worker file."""
        return FileResponse("static/service-worker.js")


class Favicon(web.View):
    """Render static favicon file."""

    async def get(self) -> web.FileResponse:
        """Render static favicon file."""
        return FileResponse("static/favicon.png")
