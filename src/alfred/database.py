"""
Created on Dec 17, 2017

@author: ionut
"""

import datetime
import json
import logging
import asyncpg

logger = logging.getLogger(__name__)


class DBClient:
    """
    Handle database communication using momoko
    """

    def __init__(self, dsn):
        self.dsn = dsn

    async def connect(self) -> None:
        """
        Initialize asyncpg Pool and connect to the database
        """

        async def init_connection(conn: asyncpg.Connection) -> None:
            await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
            # await conn.set_type_codec("geometry", encoder=encode_geometry,decoder=decode_geometry, format="binary")

        self.pool = await asyncpg.create_pool(dsn=self.dsn, min_size=2, max_size=8, init=init_connection)
        logger.info("successfully connected to database")

    async def disconnect(self) -> None:
        """
        Disconnect from PG and close pool
        """
        assert self.pool is not None
        await self.pool.close()
        logger.info("successfully disconnected from database")

    async def get_user(self, username) -> dict | None:
        """
        Return first user matching username
        :param username: data to match the username against
        :return user
        """
        query = "SELECT id,name,username,password FROM users WHERE username=$1 LIMIT 1"
        users = await self.pool.fetch(query, username)
        return dict(users[0]) if users else None

    async def add_subscription(self, subscription):
        """
        Add new subscription object
        :param subscription: subscription info from browser
        :return subscription ID
        """
        query = """INSERT INTO subscriptions(added_timestamp,endpoint,key,auth_secret)
        VALUES($1,$2,$3,$4) RETURNING id"""
        conn = await self.pool.acquire()
        try:
            result = await conn.fetch(
                query,
                datetime.datetime.now(tz=datetime.UTC),
                subscription["endpoint"],
                subscription["key"],
                subscription["authSecret"]
            )
        finally:
            await self.pool.release(conn)
        return result

    async def get_subscriptions(self):
        """
        Return all subscription objects
        :return subscriptions list
        """
        query = "SELECT id,added_timestamp,endpoint,key,auth_secret FROM subscriptions"
        conn = await self.pool.acquire()
        try:
            records = await conn.fetch(query)
        finally:
            await self.pool.release(conn)
        return [dict(record) for record in records]

    async def get_signals(self, stype=None, signal_id=None):
        """
        Return all signals onf stype or all signals if None
        :param stype: signal type (sensor, switch, camera)
        :param signal_id: signal ID for this type
        :return: list of signal
        """
        query = "SELECT id,name,stype,url,active,attributes FROM signals"
        data = []
        if stype:
            query += " WHERE stype=$1"
            data.append(stype)
            if signal_id:
                query += " AND id=$2"
                data.append(signal_id)
        query += " ORDER BY name"
        conn = await self.pool.acquire()
        try:
            records = await conn.fetch(query, *data)
        finally:
            await self.pool.release(conn)
        if not records:
            return []
        return [dict(record) for record in records]

    async def get_sensor_signals(self):
        """
        Get sensor signal data
        :returns: list of sensor signals
        """
        sensors = await self.get_signals("sensor")
        return sensors

    async def get_switch_signals(self, signal_id=None):
        """
        Get switch signal data
        :param signal_id: signal ID
        :returns: list of switch signals
        """
        switches = await self.get_signals("switch", signal_id)
        return switches

    async def get_sound_signals(self):
        """
        Get sound signal data
        :returns: list of sound signals
        """
        sounds = await self.get_signals("sound")
        return sounds

    async def get_camera_signals(self, signal_id=None):
        """
        Get camera signal data
        :param signal_id: signal ID
        :returns: list of camera signals
        """
        cameras = await self.get_signals("camera", signal_id)
        return cameras
