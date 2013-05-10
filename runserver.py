#!/usr/bin/env python
#-*- coding: utf-8 -*-
import tornado.web
import tornado.ioloop
import tornado.options
import tornado.httpserver
from tornado.options import define, options

from webgear5 import Application
from webgear5.settings import settings

define("port", default=8080, type=int)
define("autoreload", default=True, type=bool)


def main():
    tornado.options.parse_command_line()
    print '... server started on port %s ...' % options.port
    print '... debug mode: %s' % settings.get('debug', True)
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()