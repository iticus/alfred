"""
Created on Dec 18, 2017

@author: ionut
"""

import datetime
import json
import logging
import time
from urllib.parse import urlparse

import aiohttp.client
from pywebpush import WebPusher
from py_vapid import Vapid
from argon2 import PasswordHasher, exceptions

logger = logging.getLogger(__name__)


def time_to_minutes(time_value):
    """
    Convert a HH:MM string value to number of minutes since 00:00
    :param time_value: hours:minutes value to convert
    :return: number of minutes since 00:00
    """
    parts = time_value.split(":")
    return int(parts[0]) * 60 + int(parts[1])


async def control(app):
    """
    Retrieve signal value and check that schedules are implemented
    :param app: tornado application instance
    """
    error_msg = ""
    client = aiohttp.client.ClientSession()
    signals = await app.database.get_signals()
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
                response = await client.get(url)
                aux = json.loads(response.body.decode())
                value = "1" if aux.get("curvals", {}).get("torch", "") == "on" else "0"
            else:
                response = await client.get(signal["url"])
                value = response.body.decode()
        except Exception as exc:
            error_msg += "cannot retrieve signal data for %s: %s" % (
                signal["name"],
                exc,
            )
            logger.error(error_msg)
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


async def control_switch(signal, state):
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
    logger.info("changing state for URL %s, value: %s", url, state)
    response = await client.fetch(url, method=method, body=body)
    return response.body.decode()


async def play_sound(url):
    """
    Play sound using url
    :param url: sounder URL to make the POST request to
    :return: decoded response body from POST request
    """
    logger.info("playing sound for URL %s", url)
    client = aiohttp.client.ClientSession()
    response = await client.get(url, method="POST", body="{}")
    return response.body.decode()


def make_pw_hash(password: str) -> str:
    """
    Generate argon2 password hash
    :param password: password text to be hashed
    :returns: password hash
    """
    password_hasher = PasswordHasher()
    pw_hash = password_hasher.hash(password)
    return pw_hash


def compare_pwhash(pw_hash: str, password: str) -> bool:
    """
    Compute hash for current password and compare it to pw_hash
    :param pw_hash: previously generated pw_hash to be compared
    :param password: password text to compute hash for
    :returns: True or False
    """
    password_hasher = PasswordHasher()
    try:
        password_hasher.verify(pw_hash, password)
        # check rehash
        # needs_rehash = False
        # if result:
        #     needs_rehash = ph.check_needs_rehash(pw_hash)
    except exceptions.VerifyMismatchError:
        return False
    except exceptions.InvalidHash:
        logger.error("tried to decode invalid hash: %s", password)
        return False
    return True


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
        "sub": "mailto:ticus.ionut@gmail.com",
    }
    vapid_key = Vapid.from_pem(private_key=private_key_data.encode())
    headers = vapid_key.sign(vapid_claims)
    return headers


async def send_push_notification(payload, config, subscription):
    """
    Send push notification using subscription info (url and keys)
    :param payload: payload (usable) data to be sent
    :param config: configuration information from Tornado app
    :param subscription: subscription info dict (keys, endpoint)
    :return: POST request result status code
    """
    subscription_info = {
        "endpoint": subscription["endpoint"],
        "keys": {"auth": subscription["auth_secret"], "p256dh": subscription["key"]},
    }
    web_push = WebPusher(subscription_info)
    body = web_push.encode(payload, "aesgcm")
    headers = generate_vapid_headers(config.VAPID_PRIVATE_KEY, subscription["endpoint"])
    crypto_key = headers.get("Crypto-Key", "")
    if crypto_key:
        crypto_key += ";"
    crypto_key += "dh=" + body["crypto_key"].decode()
    headers.update(
        {
            "Crypto-Key": crypto_key,
            "Content-Encoding": "aesgcm",
            "Encryption": "salt=" + body["salt"].decode(),
            "TTL": "86400",
        }
    )
    client = AsyncHTTPClient()
    result = await client.fetch(subscription["endpoint"], method="POST", body=body["body"], headers=headers)
    return result.code
