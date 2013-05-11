#!/usr/bin/env python
#-*- coding: utf-8 -*-
from webgear5.models import Member
from webgear5.handlers import BaseHandler
from webgear5.settings import cache


class MainHandler(BaseHandler):
    def get(self):
        member = Member.get_by_username('Maverick')
        self.set_header('ContentType', 'application/json')
        self.write(member.json)