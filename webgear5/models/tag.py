#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from werkzeug.utils import cached_property
from webgear5.extensions import mongo, cache
from pymongo import ASCENDING


class Tag:

    def __init__(self, tag=None):
        self.id = tag['_id']
        self.tag_id = tag['tag_id']
        self.name = tag['name']
        self.screen_name = tag['screen_name']
        self.description = tag['description']
        self.followers = tag['followers']

    @cached_property
    def total(self):
        return mongo.db.topics.find({'tags': {'$in': [self.tag_id]}}).count()

    @cached_property
    def json(self):
        return dict(
            tag_id=self.tag_id,
            name=self.name,
            screen_name=self.screen_name,
            description=self.description,
            followers=self.followers,
            total=self.total
        )

    def save(self):
        tag = dict(
            _id=self.id,
            tag_id=self.tag_id,
            name=self.name,
            screen_name=self.screen_name,
            description=self.description,
            followers=self.followers
        )
        mongo.db.tags.save(tag)

    @staticmethod
    @cache.memoize(timeout=24 * 60 * 60)
    def get_tags():
        tags = mongo.db.tags.find().sort('tag_id', ASCENDING)
        if tags.count() > 0:
            return [Tag(tag) for tag in tags]
        return None

    @staticmethod
    def get_by_id(tag_id):
        tags = Tag.get_tags()
        if tags:
            for tag in tags:
                if tag.tag_id == tag_id:
                    return tag
        return None

    @staticmethod
    def get_json():
        tags = Tag.get_tags()
        return [tag.json for tag in tags] if tags else None

    @staticmethod
    def get_by_name(name):
        tags = Tag.get_tags()
        if tags:
            for tag in tags:
                if tag.name.lower() == name.lower():
                    return tag
        return None

    @staticmethod
    def get_by_screen_name(screen_name):
        tags = Tag.get_tags()
        if tags:
            for tag in tags:
                if tag.screen_name.lower() == screen_name.lower():
                    return tag
        return None


