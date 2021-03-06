"""
Created on Dec 18, 2017

@author: ionut
"""

import binascii
import datetime
import json
import logging
import os
import time
from urllib.parse import urlparse
from pywebpush import WebPusher
from py_vapid import Vapid
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient
try:
    from hashlib import pbkdf2_hmac
    from hmac import compare_digest
except ImportError:
    from backports.pbkdf2 import pbkdf2_hmac, compare_digest


def time_to_minutes(time_value):
    """
    Convert a HH:MM string value to number of minutes since 00:00
    :param time_value: hours:minutes value to convert
    :return: number of minutes since 00:00
    """
    parts = time_value.split(":")
    return int(parts[0]) * 60 + int(parts[1])


@coroutine
def control(app):
    """
    Retrieve signal value and check that schedules are implemented
    :param app: tornado application instance
    """
    error_msg = ""
    client = AsyncHTTPClient()
    signals = yield app.database.get_signals()
    now = datetime.datetime.now()
    now_minutes = time_to_minutes(now.strftime("%H:%M"))
    for signal in signals:
        if not signal["active"]:
            continue
        if signal["stype"] == "camera" or signal["stype"] == "sound":
            continue
        try:
            if signal["attributes"].get("type", "") == "android":
                url = signal["url"] + "/status.json?show_avail=1"
                response = yield client.fetch(url)
                aux = json.loads(response.body.decode())
                value = "1" if aux.get("curvals", {}).get("torch", "") == "on" else "0"
            else:
                response = yield client.fetch(signal["url"])
                value = response.body.decode()
        except Exception as exc:
            error_msg += "cannot retrieve signal data for %s: %s" % (signal["name"], exc)
            logging.error(error_msg)
            continue

        if signal["stype"] == "sensor":
            app.cache[signal["id"]] = value
            continue
        # Handle switch value and schedule
        app.cache[signal["id"]] = True if value in ["1", "1,1"] else False
        if signal["attributes"].get("schedule", None):
            start_time = signal["attributes"]["schedule"]["start"]
            start_time = time_to_minutes(start_time)
            stop_time = signal["attributes"]["schedule"]["stop"]
            stop_time = time_to_minutes(stop_time)
            if start_time <= stop_time:
                if start_time <= now_minutes < stop_time and not app.cache[signal["id"]]:
                    control_switch(signal, "1")
                    app.cache[signal["id"]] = True
                elif not (start_time <= now_minutes < stop_time) and app.cache[signal["id"]]:
                    control_switch(signal, "0")
                    app.cache[signal["id"]] = False
            else:
                if stop_time <= now_minutes < start_time and app.cache[signal["id"]]:
                    control_switch(signal, "0")
                    app.cache[signal["id"]] = False
                elif not (stop_time <= now_minutes < start_time) and not app.cache[signal["id"]]:
                    control_switch(signal, "1")
                    app.cache[signal["id"]] = True
    if error_msg:
        raise Exception(error_msg)


@coroutine
def control_switch(signal, state):
    """
    Turn switch on or off
    :param signal: signal to make handle
    :param state: desired state ("0" or "1")
    :return: decoded response body from POST request
    """
    method = "POST"
    body = "{}"
    url = signal["url"]
    if signal["attributes"].get("type") == "android":
        method = "GET"
        body = None
        if state == "1":
            url += "/enabletorch"
        else:
            url += "/disabletorch"
    else:
        if state == "1":
            url += "/turn_on"
        else:
            url += "/turn_off"
    client = AsyncHTTPClient()
    logging.info("changing state for URL %s, value: %s", url, state)
    response = yield client.fetch(url, method=method, body=body)
    return response.body.decode()


@coroutine
def play_sound(url):
    """
    Play sound using url
    :param url: sounder URL to make the POST request to
    :return: decoded response body from POST request
    """
    logging.info("playing sound for URL %s", url)
    client = AsyncHTTPClient()
    response = yield client.fetch(url, method="POST", body="{}")
    return response.body.decode()


def format_frame(frame):
    """
    Return a nice representation of frame.f_locals
    :param frame: frame object
    :returns: string representation
    """
    buf = ""
    for key, value in frame.f_locals.items():
        buf += "\t%s -> %s\n" % (key, value)
    return buf


def make_pwhash(algo, password, iterations):
    """
    Generate pbkdf2_hmac password hash using random salt and num interations
    :param algo: hashing algorithm to be use such as "sha1" or "sha256"
    :param password: password text to be hashed
    :param iterations: number of hashing runs
    :returns: algo$salt$hash
    """
    salt = binascii.hexlify(os.urandom(16))
    hsh = pbkdf2_hmac(algo, password.encode(), salt, iterations)
    hsh = binascii.hexlify(hsh)
    hsh = "%s$%s$%s" % (algo, salt.decode(), hsh.decode())
    return hsh


def compare_pwhashes(pwhash, password, iterations):
    """
    Compute hash for current password and compare it to pwhash
    :param pwhash: previously generated pwhash to be compared
    :param password: password text to compute hash for
    :param iterations: number of hashing runs
    :returns: True or False
    """
    algo, salt, hsh = pwhash.split("$")
    derived_key = pbkdf2_hmac(algo, password.encode(), salt.encode(), iterations)
    derived_key = binascii.hexlify(derived_key)
    return compare_digest(derived_key, hsh.encode())


def generate_vapid_headers(private_key_data, endpoint):
    """
    Generate vapid headers for web push call
    :param private_key_data: private key string data
    :param endpoint: endpoint URL from subscription info
    :return: vapid Authorization header
    """
    url = urlparse(endpoint)
    aud = "{}://{}".format(url.scheme, url.netloc)
    vapid_claims = {
        "aud": aud,
        "exp": int(time.time()) + 86400,
        "sub": "mailto:ticus.ionut@gmail.com"
    }
    vapid_key = Vapid.from_pem(private_key=private_key_data.encode())
    headers = vapid_key.sign(vapid_claims)
    return headers


@coroutine
def send_push_notification(payload, config, subscription):
    """
    Send push notification using subscription info (url and keys)
    :param payload: payload (usable) data to be sent
    :param config: configuration information from Tornado app
    :param subscription: subscription info dict (keys, endpoint)
    :return: POST request result status code
    """
    subscription_info = {
        "endpoint": subscription["endpoint"],
        "keys": {
            "auth": subscription["auth_secret"],
            "p256dh": subscription["key"]
        }
    }
    web_push = WebPusher(subscription_info)
    body = web_push.encode(payload, "aesgcm")
    headers = generate_vapid_headers(config.VAPID_PRIVATE_KEY, subscription["endpoint"])
    crypto_key = headers.get("Crypto-Key", "")
    if crypto_key:
        crypto_key += ";"
    crypto_key += "dh=" + body["crypto_key"].decode()
    headers.update({
        "Crypto-Key": crypto_key,
        "Content-Encoding": "aesgcm",
        "Encryption": "salt=" + body["salt"].decode(),
        "TTL": "86400"
    })
    client = AsyncHTTPClient()
    result = yield client.fetch(subscription["endpoint"], method="POST",
                                body=body["body"], headers=headers)
    return result.code
