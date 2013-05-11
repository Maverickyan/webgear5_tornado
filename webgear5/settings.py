#!/usr/bin/env python
#-*- coding: utf-8 -*-
import os
import redis
import tornadoredis

from pymongo import MongoClient
from jinja2 import Environment, FileSystemLoader
from extensions.session import RedisSessionStore
from extensions.cache import Cache

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
    session_lifetime=7,
    default_avatar_url='/static/img/avatar.jpg',
    avatar_prefix='/static/img/avatars/%s'
)

#Jinja templates setting
jinja_environment = Environment(
    loader=FileSystemLoader(settings['template_path']),
    auto_reload=settings['debug'],
    autoescape=False)

#Redis Session store
pool = redis.ConnectionPool(db=0)
rdb = redis.StrictRedis(connection_pool=pool)
session_store = RedisSessionStore(redis_connection=rdb)

#WebSocket-Redis pool
websocket_pool = tornadoredis.ConnectionPool(max_connections=500, wait_for_available=True, db=1)

#Database setting
db = MongoClient('mongodb://localhost:27017')['webgear5']
file_db = MongoClient('mongodb://localhost:27017')['webgear5']

config = dict(
    CACHE_REDIS_HOST='127.0.0.1',
    CACHE_REDIS_PORT=6379,
    CACHE_KEY_PREFIX=''
)

cache = Cache(config)
