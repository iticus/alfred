'''
Created on Dec 17, 2017

@author: ionut
'''

import logging

#Logging config
logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                    format='[%(asctime)s] - %(levelname)s - %(message)s')
logging.getLogger('tornado.access').setLevel(logging.WARNING)

#Tornado settings
ADDRESS = '0.0.0.0'
PORT = 8000
TEMPLATE_PATH = 'templates'
STATIC_PATH = 'static'

#Database settings
DSN = 'dbname=alfred user=postgres password=password host=127.0.0.1 port=5432'

#Security
PW_ITERATIONS = 100000
PW_ALGO = 'sha256'
COOKIE_SECRET = 'TO BE ADDDED' #cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1
