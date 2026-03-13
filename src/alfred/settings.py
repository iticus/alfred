"""
Created on Dec 17, 2017

@author: ionut
"""

import logging
import os

#Logging config
logging.basicConfig(level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S",
                    format="[%(asctime)s] - %(levelname)s - %(message)s")
logging.getLogger("tornado.access").setLevel(logging.WARNING)

#Tornado settings
ADDRESS = "0.0.0.0"
PORT = 8000
TEMPLATE_PATH = "templates"
STATIC_PATH = "static"

#Database settings
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DATABASE = os.getenv("POSTGRES_DB", "alfred")
DSN = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}"

# Cache settings
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "password")

#Security
PW_ITERATIONS = 100000
PW_ALGO = "sha256"
COOKIE_SECRET = os.getenv("COOKIE_SECRET")
# "RzTUnoYHGdyfoSCP4QYokjauoZeTnig6JIMuQhuiKA8OBdwRZq5gZOx65FnESa0h"

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
