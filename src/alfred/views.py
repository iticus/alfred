"""Created on Dec 17, 2017.

Copyright (C) 2026, Ionut Ticus (iticus), <ticus.ionut@gmail.com>
"""

import logging
from pathlib import Path

import aiohttp.client
import aiohttp_jinja2
from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from aiohttp_session import get_session, new_session

from alfred import appkeys, utils

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

    async def post(self) -> web.Response:
        """Handle logout request."""
        session = await get_session(self.request)
        session.invalidate()
        return web.HTTPFound(location="/")


class Home(BaseView):
    """Request Handler for "/", render home template."""

    async def get(self) -> web.Response:
        """Render home page."""
        context = {
            "vapid_public_key": self.config.VAPID_PUBLIC_KEY,
            "session": self.request.get("session", {}),
        }
        return aiohttp_jinja2.render_template("home.html", self.request, context=context)


class Sensors(BaseView):
    """Request Handler for "/sensors".

    Available methods: GET
    """

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

    async def get(self) -> web.Response:
        """Return all switches data."""
        switches = await self.database.get_switch_signals()
        for switch in switches:
            switch["value"] = await self.cache.get(f"{switch['id']}")
        return web.json_response({"status": "ok", "switches": switches})

    async def post(self) -> web.Response:
        """Toggle switch."""
        data = await self.request.json()
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

    async def get(self) -> web.Response:
        """Return all sound data."""
        sounds = await self.database.get_sound_signals()
        return web.json_response({"status": "ok", "sounds": sounds})

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

    async def get(self) -> web.Response:
        """Return all available cameras."""
        cameras = await self.database.get_camera_signals()
        return web.json_response({"status": "ok", "cameras": cameras})


class VideoHTTP(BaseView):
    """Request Handler for "/http_video/."""

    async def get(self) -> web.WebSocketResponse:
        """Serve HTTP video frames over a websocket."""
        url = self.request.query.get("url")
        if not url:
            raise web.HTTPBadRequest(text="missing URL")

        logger.info("new http_video client %s", self)
        ws = web.WebSocketResponse()
        await ws.prepare(self.request)

        async with aiohttp.client.ClientSession() as client:
            async for message in ws:
                if message.type == aiohttp.WSMsgType.TEXT:
                    if message.data == "?":
                        try:
                            async with client.get(url) as response:
                                response.raise_for_status()
                                await ws.send_bytes(await response.read())
                        except (aiohttp.ClientError, TimeoutError):
                            logger.exception("cannot handle mjpeg data")
                            await ws.close()
                            break
                    elif message.data == "!":
                        logger.info("closing websocket by client request")
                        await ws.close()
                        break
                    else:
                        await ws.send_str(message.data)
                elif message.type == aiohttp.WSMsgType.ERROR:
                    logger.error("websocket connection closed with exception %s", ws.exception())

        logger.info("removing ws http_video client %s", self)
        return ws


class Subscribe(BaseView):
    """Request Handler for "/subscribe" - handle push subscribe requests.

    Available methods: POST
    """

    async def post(self) -> web.Response:
        """Add new subscription info."""
        subscription = await self.request.json()
        result = await self.database.add_subscription(subscription)
        if not result:
            return web.json_response({"status": "error"}, status=500)
        return web.json_response({"status": "ok"})


class ServiceWorker(web.View):
    """Render static service worker file."""

    path = Path(__file__).parent / "static" / "service-worker.js"

    async def get(self) -> web.FileResponse:
        """Render static service worker file."""
        return FileResponse(self.path)


class Favicon(web.View):
    """Render static favicon file."""

    path = Path(__file__).parent / "static" / "img" / "logo_512.png"

    async def get(self) -> web.FileResponse:
        """Render static favicon file."""
        return FileResponse(self.path)
