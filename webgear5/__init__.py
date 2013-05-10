#!/usr/bin/env python
#-*- coding: utf-8 -*-
import tornado.web
import tornado.options

from tornado.web import url, StaticFileHandler
from settings import settings, jinja_environment, db, file_db, session_store
from handlers import home


class Application(tornado.web.Application):
    def __init__(self):

        handlers = [
            url(r'/static/img/(.+)', StaticFileHandler, dict(path=settings['image_path']), name='images'),
            url(r'/static/js/(.+)', StaticFileHandler, dict(path=settings['js_path']), name='js'),
            url(r'/static/css/(.+)', StaticFileHandler, dict(path=settings['css_path']), name='css'),
            url(r'/', home.MainHandler, name='home'),
        ]

        #init jinja2 environment
        self.jinja_env = jinja_environment

        #register filters for jinja2
        #self.jinja_env.filters.update(register_filters())
        self.jinja_env.tests.update({})
        self.jinja_env.globals['settings'] = settings

        tornado.web.Application.__init__(self, handlers, **settings)

        self.db = db
        self.file_db = file_db
        self.session_store = session_store