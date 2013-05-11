# -*- coding: utf-8 -*-
import uuid
import hashlib
import inspect
import exceptions
import functools
import warnings
import redis_cache
from types import NoneType


def function_namespace(f, args=None):
    """
    Attempts to returns unique namespace for function
    """
    m_args = inspect.getargspec(f)[0]

    if len(m_args) and args:
        if m_args[0] == 'self':
            return '%s.%s.%s' % (f.__module__, args[0].__class__.__name__, f.__name__)
        elif m_args[0] == 'cls':
            return '%s.%s.%s' % (f.__module__, args[0].__name__, f.__name__)

    if hasattr(f, 'im_func'):
        return '%s.%s.%s' % (f.__module__, f.im_class.__name__, f.__name__)
    elif hasattr(f, '__class__'):
        return '%s.%s.%s' % (f.__module__, f.__class__.__name__, f.__name__)
    else:
        return '%s.%s' % (f.__module__, f.__name__)


class Cache(object):
    """
    This class is used to control the cache objects.
    """

    app = {}

    def __init__(self, config=None):
        self.config = config
        self.init_app(config)

    def init_app(self, config=None):
        if not isinstance(config, (NoneType, dict)):
            raise ValueError("`config` must be an instance of dict or NoneType")

        if config is None:
            config = self.config

        config.setdefault('CACHE_DEFAULT_TIMEOUT', 300)
        config.setdefault('CACHE_THRESHOLD', 500)
        config.setdefault('CACHE_KEY_PREFIX', '')
        config.setdefault('CACHE_MEMCACHED_SERVERS', None)
        config.setdefault('CACHE_DIR', None)
        config.setdefault('CACHE_OPTIONS', None)
        config.setdefault('CACHE_ARGS', [])
        config.setdefault('CACHE_TYPE', 'redis')
        config.setdefault('CACHE_NO_NULL_WARNING', False)

        if config['CACHE_TYPE'] == 'null' and not config['CACHE_NO_NULL_WARNING']:
            warnings.warn("CACHE_TYPE is set to null, "
                          "caching is effectively disabled.")

        self._set_cache(config)

    def _set_cache(self, config):
        import_me = config['CACHE_TYPE']

        try:
            cache_obj = getattr(redis_cache, import_me)
        except AttributeError:
            raise ImportError("%s is not a valid FlaskCache backend" % (
                              import_me))

        cache_args = config['CACHE_ARGS'][:]
        cache_options = {'default_timeout': config['CACHE_DEFAULT_TIMEOUT']}

        if config['CACHE_OPTIONS']:
            cache_options.update(config['CACHE_OPTIONS'])

        self.app.setdefault('cache', {})
        self.app['cache'][self] = cache_obj(config, cache_args, cache_options)

    @property
    def cache(self):
        return self.app['cache'][self]

    def get(self, *args, **kwargs):
        """Proxy function for internal cache object."""
        return self.cache.get(*args, **kwargs)

    def set(self, *args, **kwargs):
        """Proxy function for internal cache object."""
        self.cache.set(*args, **kwargs)

    def add(self, *args, **kwargs):
        """Proxy function for internal cache object."""
        self.cache.add(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Proxy function for internal cache object."""
        self.cache.delete(*args, **kwargs)

    def delete_many(self, *args, **kwargs):
        """Proxy function for internal cache object."""
        self.cache.delete_many(*args, **kwargs)

    def clear(self):
        """Proxy function for internal cache object."""
        self.cache.clear()

    def get_many(self, *args, **kwargs):
        """Proxy function for internal cache object."""
        return self.cache.get_many(*args, **kwargs)

    def set_many(self, *args, **kwargs):
        """Proxy function for internal cache object."""
        self.cache.set_many(*args, **kwargs)

    def cached(self, timeout=None, key_prefix='view/%s', unless=None):

        def decorator(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                #: Bypass the cache entirely.
                if callable(unless) and unless() is True:
                    return f(*args, **kwargs)

                try:
                    cache_key = decorated_function.make_cache_key(*args, **kwargs)
                    rv = self.cache.get(cache_key)
                except Exception:
                    return f(*args, **kwargs)

                if rv is None:
                    rv = f(*args, **kwargs)
                    try:
                        self.cache.set(cache_key, rv, timeout=decorated_function.cache_timeout)
                    except Exception:
                        return f(*args, **kwargs)
                return rv

            def make_cache_key(*args, **kwargs):
                if callable(key_prefix):
                    cache_key = key_prefix()
                else:
                    cache_key = key_prefix

                cache_key = cache_key.encode('utf-8')

                return cache_key

            decorated_function.uncached = f
            decorated_function.cache_timeout = timeout
            decorated_function.make_cache_key = make_cache_key

            return decorated_function
        return decorator

    def _memvname(self, funcname):
        return funcname + '_memver'

    def memoize_make_version_hash(self):
        return uuid.uuid4().bytes.encode('base64')[:6]

    def memoize_make_cache_key(self, make_name=None):
        """
        Function used to create the cache_key for memoized functions.
        """
        def make_cache_key(f, *args, **kwargs):
            fname = function_namespace(f, args)

            version_key = self._memvname(fname)
            version_data = self.cache.get(version_key)

            if version_data is None:
                version_data = self.memoize_make_version_hash()
                self.cache.set(version_key, version_data)

            cache_key = hashlib.md5()

            #: this should have to be after version_data, so that it
            #: does not break the delete_memoized functionality.
            if callable(make_name):
                altfname = make_name(fname)
            else:
                altfname = fname

            if callable(f):
                keyargs, keykwargs = self.memoize_kwargs_to_args(f,
                                                                 *args,
                                                                 **kwargs)
            else:
                keyargs, keykwargs = args, kwargs

            try:
                updated = "{0}{1}{2}".format(altfname, keyargs, keykwargs)
            except AttributeError:
                updated = "%s%s%s" % (altfname, keyargs, keykwargs)

            cache_key.update(updated)
            cache_key = cache_key.digest().encode('base64')[:16]
            cache_key += version_data

            return cache_key
        return make_cache_key

    def memoize_kwargs_to_args(self, f, *args, **kwargs):

        new_args = []
        arg_num = 0
        argspec = inspect.getargspec(f)

        args_len = len(argspec.args)
        for i in range(args_len):
            if i == 0 and argspec.args[i] in ('self', 'cls'):
                arg = repr(args[0])
                arg_num += 1
            elif argspec.args[i] in kwargs:
                arg = kwargs[argspec.args[i]]
            elif arg_num < len(args):
                arg = args[arg_num]
                arg_num += 1
            elif abs(i-args_len) <= len(argspec.defaults):
                arg = argspec.defaults[i-args_len]
                arg_num += 1
            else:
                arg = None
                arg_num += 1

            new_args.append(arg)

        return tuple(new_args), {}

    def memoize(self, timeout=None, make_name=None, unless=None):

        def memoize(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                #: bypass cache
                if callable(unless) and unless() is True:
                    return f(*args, **kwargs)

                try:
                    cache_key = decorated_function.make_cache_key(f, *args, **kwargs)
                    rv = self.cache.get(cache_key)
                except Exception:
                    return f(*args, **kwargs)

                if rv is None:
                    rv = f(*args, **kwargs)
                    try:
                        self.cache.set(cache_key, rv, timeout=decorated_function.cache_timeout)
                    except Exception:
                        return f(*args, **kwargs)
                return rv

            decorated_function.uncached = f
            decorated_function.cache_timeout = timeout
            decorated_function.make_cache_key = self.memoize_make_cache_key(make_name)
            decorated_function.delete_memoized = lambda: self.delete_memoized(f)

            return decorated_function
        return memoize

    def delete_memoized(self, f, *args, **kwargs):

        if not callable(f):
            raise exceptions.DeprecationWarning("Deleting messages by relative name is no longer"
                                                " reliable, please switch to a function reference")

        _fname = function_namespace(f, args)

        try:
            if not args and not kwargs:
                version_key = self._memvname(_fname)
                version_data = self.memoize_make_version_hash()
                self.cache.set(version_key, version_data)
            else:
                cache_key = f.make_cache_key(f.uncached, *args, **kwargs)
                self.cache.delete(cache_key)
        except Exception:
            pass

    def delete_memoized_verhash(self, f, *args):

        if not callable(f):
            raise exceptions.DeprecationWarning("Deleting messages by relative name is no longer"
                                                " reliable, please use a function reference")

        _fname = function_namespace(f, args)

        try:
            version_key = self._memvname(_fname)
            self.cache.delete(version_key)
        except Exception:
            pass