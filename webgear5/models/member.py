#!/usr/bin/env python
#-*- coding: utf-8 -*-
import re
from hashlib import md5
from bson.son import SON
from urllib import unquote
from datetime import datetime
from pymongo import DESCENDING, ASCENDING
from webgear5.settings import db, settings, cache
from webgear5.helpers import cached_property


class Member:

    BANNED = 1 << 0
    MEMBER = 1 << 1
    VIP = 1 << 3
    MODERATOR = 1 << 7
    ADMIN = 1 << 8

    def __init__(self, member=None):
        self.username = member.get('username')
        self.email = member.get('email')
        self.registered_date = member.get('registered_date', datetime.utcnow())
        self.last_login = member.get('last_login', datetime.utcnow())
        self.login_date = member.get('login_date', datetime.utcnow())
        self.roles = member.get('roles', self.MEMBER)
        self.ip_address = member.get('ip_address', '')
        self.profile = Profile(member.get('profile', {}))
        self.settings = Settings(member.get('settings', {}))
        self.token = member.get('token', '')

    @property
    def is_banned(self):
        return self.roles & self.BANNED == self.BANNED

    @property
    def is_admin(self):
        return self.roles & self.ADMIN == self.ADMIN

    @property
    def is_moderator(self):
        return True if self.is_admin else self.roles & self.MODERATOR == self.MODERATOR

    @property
    def is_vip(self):
        return self.roles & self.VIP == self.VIP

    @property
    def is_member(self):
        return self.roles & self.MEMBER == self.MEMBER

    @property
    def is_senior(self):
        delta = datetime.utcnow() - self.registered_date.replace(tzinfo=None)
        if delta.days > (365 * 8):
            return True
        return False

    @property
    def avatar_url(self):
        if not self.profile.avatar_url:
            return settings.get('default_avatar_url', '')
        prefix = settings.get('avatar_url', '%s')
        return prefix % self.profile.avatar_url

    @property
    def nickname(self):
        if self.settings.show_nickname and 0 < len(self.profile.nickname) <= 8:
            return self.profile.nickname
        return self.username

    @cached_property
    def user_roles(self):
        user_roles = []
        if self.is_admin:
            user_roles.append(Member.ADMIN)
        if self.is_moderator:
            user_roles.append(Member.MODERATOR)
        if self.is_vip:
            user_roles.append(Member.VIP)
        if self.is_member:
            user_roles.append(Member.MEMBER)
        if self.is_banned:
            user_roles.append(Member.BANNED)

        return user_roles

    @cached_property
    def total_topics(self):
        return db.topics.find({'username': self.username}).count()

    @cached_property
    def total_replies(self):
        return db.posts.find({'username': self.username, 'index_id': {'$gt': 0}}).count()

    @cached_property
    def total_primes(self):
        return db.topics.find({'username': self.username, 'is_prime': True}).count()

    @property
    def json(self):
        return dict(
            username=self.username,
            email=self.email,
            registered_date=self.registered_date.isoformat(),
            last_login=self.last_login.isoformat(),
            login_date=self.login_date.isoformat(),
            roles=self.roles,
            ip_address=self.ip_address,
            profile=self.profile.jsonify(),
            settings=self.settings.jsonify()
        )

    @staticmethod
    def get_members(page=1, size=50):
        members = db.members.find()\
            .sort('registered_date', DESCENDING)\
            .skip((page - 1) * size)\
            .limit(size)

        if members.count(True) == 0:
            return [], 0

        return [Member(member) for member in members], members.count()

    @staticmethod
    @cache.memoize()
    def get_by_username(username):
        member = db.members.find_one({'username': username})
        return Member(member) if member else None

    @staticmethod
    def search_by_username(username):
        username = unquote(username)
        name = '^%s$' % username.replace('[', '\[').replace(']', '\]')
        return db.members.find_one({
            'username': re.compile(name, re.IGNORECASE)
        })

    @staticmethod
    def search_by_email(email):
        name = "^%s$" % email
        return db.members.find_one({
            'email': re.compile(name, re.IGNORECASE)
        })

    @staticmethod
    def search_by_nickname(nickname):
        name = '^%s$' % nickname
        return db.members.find_one({
            'profile.nickname': re.compile(name, re.IGNORECASE)
        })

    @staticmethod
    def admin_search(username, page=1, size=50):
        username = unquote(username)
        name = r'%s' % username.replace('[', '\[').replace(']', '\]')
        members = db.members.find({
            '$or': [
                {'username': re.compile(name, re.IGNORECASE)},
                {'profile.nickname': re.compile(name, re.IGNORECASE)},
                {'email': re.compile(name, re.IGNORECASE)}
            ]
        }).sort('registered_date', DESCENDING)\
            .skip((page - 1) * size)\
            .limit(size)

        if members.count(True) == 0:
            return [], 0
        return [Member(member) for member in members], members.count()

    @staticmethod
    def search(username, page=1, size=20):
        username = unquote(username)
        name = r'%s' % username.replace('[', '\[').replace(']', '\]')
        members = db.members.find({
            '$or': [
                {'username': re.compile(name, re.IGNORECASE)}
            ]
        }).sort('username', ASCENDING)\
            .skip((page - 1) * size)\
            .limit(size)

        if members.count(True) == 0:
            return [], 0
        return [Member(member) for member in members], members.count()

    @staticmethod
    def login(username, password, ip_address):
        member = Member.search_by_username(username)
        if member and member['password'] == md5(password).hexdigest():
            member['last_login'] = member['login_date']
            member['login_date'] = datetime.now()
            member['ip_address'] = ip_address
            member['last_ip'] = member['ip_address']
            db.members.save(member)
            return member
        return None

    @staticmethod
    def has_permission(username, permission):
        member = db.members.find_one({'username': username})
        if member and member['roles'] & permission == permission:
            return True
        return False

    @staticmethod
    def get_roles():
        return [Member.BANNED, Member.MEMBER, Member.VIP, Member.MODERATOR, Member.ADMIN]

    @staticmethod
    def get_roles_json():
        return [
            dict(id=Member.BANNED, name=u'被禁止用户'),
            dict(id=Member.MEMBER, name=u'注册用户'),
            dict(id=Member.VIP, name=u'VIP'),
            dict(id=Member.MODERATOR, name=u'版主'),
            dict(id=Member.ADMIN, name=u'管理员')
        ]

    @staticmethod
    def get_top_topics_users(size=10):
        result = db.topics.aggregate([
            {'$group': {'_id': '$username',  'count': {'$sum': 1}}},
            {'$sort': SON([('count', -1), ('_id', -1)])},
            {'$limit': size}
        ])
        return result['result']


class Profile(object):

    def __init__(self, profile=None):
        self.nickname = profile.get('nickname', '')
        self.gender = profile.get('gender', 1)
        self.avatar_url = profile.get('avatar_url', '')
        self.signature = profile.get('signature', '')
        self.points = profile.get('points', 10)
        self.usable_points = profile.get('usable_points', 10)
        self.birth_date = profile.get('birth_date', datetime.min)
        self.homepage = profile.get('homepage', '')
        self.location = profile.get('location', '')
        self.contact = profile.get('contact', {})

    def jsonify(self):
        return dict(
            nickname=self.nickname,
            gender=self.gender,
            avatar_url=self.avatar_url,
            signature=self.signature,
            points=self.points,
            usable_points=self.usable_points,
            birth_date=self.birth_date.isoformat(),
            homepage=self.homepage,
            location=self.location
        )


class Settings(object):

    def __init__(self, settings=None):
        self.time_zone = settings.get('time_zone', 'Asia/Shanghai')
        self.show_nickname = settings.get('show_nickname', False)
        self.show_signature = settings.get('show_signature', False)

    def jsonify(self):
        return dict(
            time_zone=self.time_zone,
            show_nickname=self.show_nickname,
            show_signature=self.show_signature
        )

