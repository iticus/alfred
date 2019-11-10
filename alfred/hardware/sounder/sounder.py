"""
Created on Jun 7, 2018

@author: ionut
"""

import logging
import subprocess
import tornado.ioloop
import tornado.web


_FILENAMES = ["odi.mp3"]

class MainHandler(tornado.web.RequestHandler):
    """
    Request Handler for "/", render default message
    """


    def get(self):
        self.finish("hey")


class SoundHandler(tornado.web.RequestHandler):
    """
    Request Handler for playing sound
    """

    def post(self):
        filename = self.get_query_argument("filename", "")
        if filename not in _FILENAMES:
            self.set_status("404")
            return self.finish("invalid filename")

        logging.info("play %s", filename)
        subprocess.call(["mpg123", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return self.finish("OK")


def make_app():
    """
    Create main Tornado app and return it
    """
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/play/?", SoundHandler),
    ])


def main():
    """
    Main function
    """
    logging.basicConfig(level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S",
                        format="[%(asctime)s] - %(levelname)s - %(message)s")
    app = make_app()
    logging.info("starting sound on 8000")
    app.listen(8000)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
