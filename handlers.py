'''
Created on Dec 17, 2017

@author: ionut
'''

import tornado.web
from tornado.httpclient import AsyncHTTPClient


class BaseHandler(tornado.web.RequestHandler):
    """Base Handler to be inherited / implemented by subsequent handlers"""

    def get_current_user(self):
        return self.get_secure_cookie('username')


    def initialize(self):
        self.config = self.application.config
        self.db_client = self.application.database


class HomeHandler(BaseHandler):
    """Request Handler for "/", render home template"""


    def get(self):
        self.render('home.html')


class SwitchesHandler(BaseHandler):
    """Request Handler for "/switches"
    Available methods: GET, POST
    """


    @tornado.gen.coroutine
    def get(self):
        """Return all switches data"""
        switches = yield self.db_client.get_switch_signals()
        for switch in switches:
            switch['value'] = self.application.cache.get(switch['id'], None)
        self.finish({'status': 'OK', 'switches': switches})


    @tornado.gen.coroutine
    def post(self):
        """Toggle switch"""
        sid = int(self.get_argument('sid'))
        url = self.get_argument('url')
        state = self.get_argument('state')
        if state == '1':
            url += '/turn_on'
        else:
            url += '/turn_off'
        client = AsyncHTTPClient()
        response = yield client.fetch(url, method='POST', body='{}')
        if response.body.decode() != 'OK':
            return self.finish({'status': 'error'})
        self.application.cache[sid] = True if state == '1' else False
        self.finish({'status': 'OK'})


class CamerasHandler(BaseHandler):
    """Request Handler for "/cameras/"
    Available methods: GET
    """


    @tornado.gen.coroutine
    def get(self):
        """Return all available cameras or single camera data"""
        sid = self.get_argument('sid', None)
        url = self.get_argument('url', None)
        if not sid or not url:
            cameras = yield self.db_client.get_camera_signals()
            return self.finish({'status': 'OK', 'cameras': cameras})
        
        sid = int(sid)
        url = url + '/?action=snapshot'
        client = AsyncHTTPClient()
        response = yield client.fetch(url)
        self.finish(response.body)


class AboutHandler(BaseHandler):
    """Request Handler for "/about"
    Available methods: GET
    """


    @tornado.gen.coroutine
    def get(self):
        """Return available street data for locality_id, text"""
        self.render('home.html')
