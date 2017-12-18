'''
Created on Dec 18, 2017

@author: ionut
'''

import logging
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient


@coroutine
def control(app):
    """
    Retrieve signal value and check that schedules are implemented
    :param app: tornado application instance
    """
    client = AsyncHTTPClient()
    signals = yield app.database.get_switch_signals()
    for signal in signals:
        try:
            response = yield client.fetch(signal['url'])
        except Exception as exc:
            logging.error('cannot retrieve signal data for %s: %s', signal['name'], exc)
            continue
        value = response.body.decode()
        app.cache[signal['id']] = True if value in ['1', '1,1'] else False

    #TODO: implement schedules


def format_frame(frame):
    """
    Return a nice representation of frame.f_locals
    :param frame: frame object
    :returns: string representation
    """
    buf = ''
    for key, value in frame.f_locals.items():
        buf += '\t%s -> %s\n' % (key, value)
    return buf
