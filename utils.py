'''
Created on Dec 18, 2017

@author: ionut
'''

import datetime
import logging
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient


def time_to_minutes(time_value):
    """
    Convert a HH:MM string value to number of minutes since 00:00
    :param time_value: hours:minutes value to convert
    :return: number of minutes since 00:00
    """
    parts = time_value.split(':')
    return int(parts[0]) * 60 + int(parts[1])


@coroutine
def control(app):
    """
    Retrieve signal value and check that schedules are implemented
    :param app: tornado application instance
    """
    client = AsyncHTTPClient()
    signals = yield app.database.get_signals()
    now = datetime.datetime.now()
    now_minutes = time_to_minutes(now.strftime('%H:%M'))
    for signal in signals:
        if signal['stype'] == 'camera':
            continue
        try:
            response = yield client.fetch(signal['url'])
        except Exception as exc:
            logging.error('cannot retrieve signal data for %s: %s', signal['name'], exc)
            continue
        value = response.body.decode()
        if signal['stype'] == 'sensor':
            app.cache[signal['id']] = value
            continue
        #Handle switch value and schedule
        app.cache[signal['id']] = True if value in ['1', '1,1'] else False
        if signal['attributes'].get('schedule', None):
            start_time = signal['attributes']['schedule']['start']
            start_time = time_to_minutes(start_time)
            stop_time = signal['attributes']['schedule']['stop']
            stop_time = time_to_minutes(stop_time)
            if start_time <= stop_time:
                if start_time <= now_minutes < stop_time and not app.cache[signal['id']]:
                    control_switch(signal['url'], '1')
                    app.cache[signal['id']] = True
                elif not (start_time <= now_minutes < stop_time) and app.cache[signal['id']]:
                    control_switch(signal['url'], '0')
                    app.cache[signal['id']] = False
            else:
                if stop_time <= now_minutes < start_time and app.cache[signal['id']]:
                    control_switch(signal['url'], '0')
                    app.cache[signal['id']] = False
                elif not (stop_time <= now_minutes < start_time) and not app.cache[signal['id']]:
                    control_switch(signal['url'], '1')
                    app.cache[signal['id']] = True


@coroutine
def control_switch(url, state):
    """
    Turn switch on or off
    :param url: switch URL to make the POST request to
    :param state: desired state ('0' or '1')
    :return: decoded response body from POST request
    """
    logging.info('changing state for URL %s, value: %s', url, state)
    if state == '1':
        url += '/turn_on'
    else:
        url += '/turn_off'
    client = AsyncHTTPClient()
    response = yield client.fetch(url, method='POST', body='{}')
    return response.body.decode()


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
