'''
Created on Dec 17, 2017

@author: ionut
'''

import logging
import momoko
import psycopg2
from tornado.gen import coroutine


class DBClient(object):
    """
    Handle database communication using momoko
    """


    def __init__(self, dsn, ioloop=None):
        self.dsn = dsn
        self.ioloop = ioloop
        self.connected = False


    @coroutine
    def connect(self):
        self.connection = momoko.Pool(dsn=self.dsn, ioloop=self.ioloop, raise_connect_errors=True,
                                      cursor_factory=psycopg2.extras.RealDictCursor, size=2)
        result = yield self.connection.connect()
        logging.debug('connected to database, %s', result)
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
            logging.error('cannot execute query %s: %s', query, exc)
            return False

        if cursor.rowcount > 0:
            result = cursor.fetchall()
            logging.debug('got %d results', len(result))
            return result

        return True


    @coroutine
    def get_switch_signals(self):
        """
        Get light signal data
        :returns: list of light signals
        """
        query = "SELECT id,name,url,attributes FROM signals where stype='switch'"
        switches = yield self.raw_query(query)
        return switches


    @coroutine
    def get_camera_signals(self):
        """
        Get camera signal data
        :returns: list of camera signals
        """
        query = "SELECT id,name,url,attributes FROM signals where stype='camera'"
        cameras = yield self.raw_query(query)
        return cameras
