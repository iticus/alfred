"""
Created on 2026-03-13

@author: iticus
"""

import types

from aiohttp import web
from redis.asyncio import Redis

from alfred.database import DBClient

config = web.AppKey("config", types.ModuleType)
database = web.AppKey("database", DBClient)
cache = web.AppKey("cache", Redis)
