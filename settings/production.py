"""
Created on Dec 17, 2017

@author: ionut
"""

import logging

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
DSN = "dbname=alfred user=postgres password=password host=127.0.0.1 port=5432"

#Security
PW_ITERATIONS = 100000
PW_ALGO = "sha256"
COOKIE_SECRET = "TO BE ADDDED" #cat /dev/urandom | tr -dc "a-zA-Z0-9" | fold -w 64 | head -n 1

#vapid --gen
#vapid --applicationServerKey
VAPID_PRIVATE_KEY = open("/etc/ssl/private/iticus_vapid.key").read()
VAPID_PUBLIC_KEY = "BFOSZb49bLjuz1J_ZLHOlWaaPS9p8X3VDaV-c6i4V9-0jCYA9EtXqoxhC42x3vR_1cOZ2Pyj-vQ4SbRVFah7jxM"
