"""
Created on Dec 18, 2017

@author: ionut
"""

import logging
from asyncio import subprocess
from shlex import quote

from aiohttp import web

logger = logging.getLogger(__name__)


class Main(web.View):
    """
    Request Handler for "/", render default value -1
    """

    async def get(self):
        return web.Response(body="-1")


class ControlHandler(web.View):
    """
    Request Handler for toggling ON/OFF state
    """

    async def post(self):
        logger.info("got command %s", self.request.path_qs)
        cmd = quote("sudo r433mhz 11111 1 0")
        proc = await subprocess.create_subprocess_shell(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        logger.debug("%s exited with", cmd, proc.returncode)
        if stdout:
            logger.info("command stdout %s", stdout)
        if stderr:
            logger.error("command stdout %s", stderr)
        return web.Response(body="ok")


def make_app() -> web.Application:
    """
    Create main Tornado app and return it
    """
    app = web.Application()
    app.router.add_view("/", Main)
    app.router.add_view("/turn_on{tail:.*?}", ControlHandler)
    app.router.add_view("/turn_off{tail:.*?}", ControlHandler)
    return app


def main() -> None:
    """
    Main function
    """
    logging.basicConfig(
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="[%(asctime)s] - %(levelname)s - %(message)s",
    )
    application = make_app()
    web.run_app(application, host="0.0.0.0", port=8080, access_log=None)


if __name__ == "__main__":
    main()
