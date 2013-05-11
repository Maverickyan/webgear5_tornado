#!/usr/bin/env python
#-*- coding: utf-8 -*-
import tornado.web
import tornado.locale
from webgear5.extensions.session import RedisSession


class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        user = self.session['user'] if 'user' in self.session else None
        return user

    @property
    def session(self):
        if hasattr(self, '_session'):
            return self._session
        else:
            self.require_setting('session_lifetime', 'session')
            expires = self.settings['session_lifetime'] or None
            session_id = self.get_secure_cookie('sid')
            self._session = RedisSession(self.application.session_store, session_id, expires_days=expires)
            if not session_id:
                self.set_secure_cookie('sid', self._session.id, expires_days=expires)
            return self._session

    def get_user_locale(self):
        code = self.get_cookie('lang', self.settings.get('default_locale', 'zh_CN'))
        return tornado.locale.get(code)

    @property
    def is_xhr(self):
        return self.request.headers.get('X-Requested-With', '').lower() == 'xmlhttprequest'

    @property
    def is_pjax(self):
        pjax_header = self.request.headers.get('X-PJAX', None)
        pjax_args = self.get_argument('_pjax', None)
        if pjax_header or pjax_args:
            return True
        return False

    def render_string(self, template_name, **context):
        context.update(dict(
            xsrf=self.xsrf_form_html,
            request=self.request,
            user=self.current_user,
            static=self.static_url,
            handler=self,
            reverse_url=self.reverse_url
        ))

        return self._jinja_render(
            path=self.get_template_path(),
            filename=template_name,
            auto_reload=self.settings['debug'],
            **context
        )

    def _jinja_render(self, path, filename, **context):
        template = self.application.jinja_env.get_template(filename, parent=path)
        self.write(template.render(**context))