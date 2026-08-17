"""Created on 2026-03-13.

Copyright (C) 2026, Ionut Ticus (iticus), <ticus.ionut@gmail.com>
"""

import types

from aiohttp import web
from redis.asyncio import Redis

from alfred.database import DBClient

config = web.AppKey("config", types.ModuleType)
database = web.AppKey("database", DBClient)
cache = web.AppKey("cache", Redis)
