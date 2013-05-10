#!/usr/bin/env python
#-*- coding: utf-8 -*-
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import redis

from pymongo import MongoClient
from jinja2 import Environment, FileSystemLoader

root = os.path.dirname(__file__)

settings = dict(
    debug=True,
    xsrf_cookies=True,
    cookie_secret='MTkwNzk2ZDItNjk2ZS00MGFmLTg2Y2UtOWIxZmIwYTIxNWNm',
    gzip=True,
    login_url='/account/login',
    template_path=os.path.join(root, 'templates'),
    static_path=os.path.join(root, 'static'),
    image_path=os.path.join(root, 'static/img'),
    js_path=os.path.join(root, 'static/js'),
    css_path=os.path.join(root, 'static/css'),
)

#Jinja templates setting
jinja_environment = Environment(
    loader=FileSystemLoader(settings['template_path']),
    auto_reload=settings['debug'],
    autoescape=False)

#Database setting
db = MongoClient('mongodb://localhost:27017')['webgear5']
file_db = MongoClient('mongodb://localhost:27017')['webgear5']
redis_server = redis.StrictRedis()