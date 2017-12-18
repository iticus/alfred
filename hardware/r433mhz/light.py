'''
Created on Dec 18, 2017

@author: ionut
'''

import logging
import os
import tornado.ioloop
import tornado.web


class MainHandler(tornado.web.RequestHandler):
    """
    Request Handler for "/", render default value -1
    """


    def get(self):
        self.finish("-1")


class ControlHandler(tornado.web.RequestHandler):
    """
    Request Handler for toggling ON/OFF state
    """

    def post(self):
        logging.info('got command %s', self.request.uri)
        os.system('sudo r433mhz 11111 1 0')
        self.finish("OK")


def make_app():
    """
    Create main Tornado app and return it
    """
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/turn_on/?", ControlHandler),
        (r"/turn_off/?", ControlHandler),
    ])


def main():
    """
    Main function
    """
    logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                        format='[%(asctime)s] - %(levelname)s - %(message)s')
    app = make_app()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
