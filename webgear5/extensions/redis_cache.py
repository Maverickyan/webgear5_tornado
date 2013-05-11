#!/usr/bin/env python
#-*- coding: utf-8 -*-
from werkzeug.contrib.cache import RedisCache
from redis import from_url as redis_from_url


def redis(config, args, kwargs):
    kwargs.update(dict(
        host=config.get('CACHE_REDIS_HOST', 'localhost'),
        port=config.get('CACHE_REDIS_PORT', 6379),
    ))
    password = config.get('CACHE_REDIS_PASSWORD')
    if password:
        kwargs['password'] = password

    key_prefix = config.get('CACHE_KEY_PREFIX')
    if key_prefix:
        kwargs['key_prefix'] = key_prefix

    db_number = config.get('CACHE_REDIS_DB')
    if db_number:
        kwargs['db'] = db_number

    redis_url = config.get('CACHE_REDIS_URL')
    if redis_url:
        kwargs['host'] = redis_from_url(
            redis_url,
            db=kwargs.pop('db', None),
        )

    return RedisCache(*args, **kwargs)