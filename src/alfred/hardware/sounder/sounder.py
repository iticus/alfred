"""
Created on Jun 7, 2018

@author: ionut
"""

import asyncio
import logging
import subprocess

from aiohttp import web


logger = logging.getLogger(__name__)
_FILENAMES = ["odi.mp3"]


def play_file(filename: str) -> None:
    """
    Play file using mpg executable
    Args:
        filename: sound file to play
    """
    subprocess.call(["mpg123", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Main(web.View):
    """
    Request Handler for "/", render default message
    """

    async def get(self):
        return web.Response(body="hey")


class Sound(web.View):
    """
    Request Handler for playing sound
    """

    async def post(self):
        data = await self.post()
        filename = data.get("filename", "")
        if filename not in _FILENAMES:
            return web.Response(body="invalid filename", status=404)
        logger.info("playing file %s", filename)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, play_file, filename)
        return web.Response(body="ok")


def make_app() -> web.Application:
    """
    Create main web app and return it
    """
    app = web.Application()
    app.router.add_view("/", Main),
    app.router.add_view("/play{tail:.*?}", Sound)
    return app


def main() -> None:
    """
    Main function
    """
    logging.basicConfig(
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="[%(asctime)s] - %(levelname)s - %(message)s"
    )
    application = make_app()
    web.run_app(application, host="0.0.0.0", port=8000, access_log=None)


if __name__ == "__main__":
    main()
