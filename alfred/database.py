"""
Created on Dec 17, 2017

@author: ionut
"""

import datetime
import logging
import momoko
import psycopg2
from tornado.gen import coroutine


class DBClient:
    """
    Handle database communication using momoko
    """

    def __init__(self, dsn, io_loop=None):
        self.dsn = dsn
        self.io_loop = io_loop
        self.connection = None
        self.connected = False

    @coroutine
    def connect(self):
        """
        Initialize momoko Pool and connect to the database
        """
        self.connection = momoko.Pool(dsn=self.dsn, ioloop=self.io_loop, raise_connect_errors=True,
                                      cursor_factory=psycopg2.extras.RealDictCursor, size=2)
        result = yield self.connection.connect()
        logging.debug("connected to database, %s", result)
        self.connected = True

    @coroutine
    def raw_query(self, query, params=None):
        """
        Run query with specified parameters and return results if any
        :param query: SQL query text
        :param params: tuple containing parameters
        :returns database objects or True/False for success/failure
        """
        if not self.connected:
            yield self.connect()

        try:
            cursor = yield self.connection.execute(query, params)
        except psycopg2.Error as exc:
            logging.error("cannot execute query %s: %s", query, exc)
            return False

        if cursor.rowcount > 0:
            result = cursor.fetchall()
            logging.debug("got %d results", len(result))
            return result

        return []

    @coroutine
    def get_user(self, username):
        """
        Return first user matching username
        :param username: data to match the username against
        :return user
        """
        query = "SELECT id,name,username,password FROM users WHERE username=%s"
        data = (username, )
        users = yield self.raw_query(query, data)
        if not users:
            return []
        return users[0]

    @coroutine
    def add_subscription(self, subscription):
        """
        Add new subscription object
        :param subscription: subscription info from browser
        :return subscription ID
        """
        query = """INSERT INTO subscriptions(added_timestamp,endpoint,key,auth_secret)
        VALUES(%s,%s,%s,%s) RETURNING id"""
        data = (datetime.datetime.utcnow(), subscription["endpoint"], subscription["key"],
                subscription["authSecret"])
        result = yield self.raw_query(query, data)
        return result

    @coroutine
    def get_subscriptions(self):
        """
        Return all subscription objects
        :return subscriptions list
        """
        query = "SELECT id,added_timestamp,endpoint,key,auth_secret FROM subscriptions"
        subscriptions = yield self.raw_query(query)
        return subscriptions

    @coroutine
    def get_signals(self, stype=None):
        """
        Return all signals onf stype or all signals if None
        :param stype: signal type (sensor, switch, camera)
        :return: list of signal
        """
        query = "SELECT id,name,stype,url,active,attributes FROM signals"
        data = []
        if stype:
            query += " WHERE stype=%s ORDER BY name"
            data.append(stype)
        signals = yield self.raw_query(query, data)
        if not signals:
            return []
        return signals

    @coroutine
    def get_sensor_signals(self):
        """
        Get sensor signal data
        :returns: list of sensor signals
        """
        sensors = yield self.get_signals("sensor")
        return sensors

    @coroutine
    def get_switch_signals(self):
        """
        Get switch signal data
        :returns: list of switch signals
        """
        switches = yield self.get_signals("switch")
        return switches

    @coroutine
    def get_sound_signals(self):
        """
        Get sound signal data
        :returns: list of sound signals
        """
        sounds = yield self.get_signals("sound")
        return sounds

    @coroutine
    def get_camera_signals(self):
        """
        Get camera signal data
        :returns: list of camera signals
        """
        cameras = yield self.get_signals("camera")
        return cameras
