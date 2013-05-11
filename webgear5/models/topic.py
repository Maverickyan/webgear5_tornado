import time
from datetime import datetime, timedelta
from pymongo import DESCENDING
from werkzeug.utils import cached_property
from webgear5.settings import db, cache, settings
from .favorite import Favorite
from .member import Member
from .tag import Tag


class Topic:

    NORMAL = 0
    IMAGE = 1 << 0
    VIDEO = 1 << 1
    CHECKIN = 1 << 2
    LOCKED = 1 << 3

    def __init__(self, topic=None):
        self.id = topic.get('_id', '')
        self.topic_id = topic.get('topic_id', 0)
        self.subject = topic.get('subject', '')
        self.username = topic.get('username', '')
        self.post_date = topic.get('post_date', datetime.utcnow())
        self.last_username = topic.get('last_username', '')
        self.last_post_date = topic.get('last_post_date', datetime.min)
        self.flags = topic.get('flags', 0)
        self.views = topic.get('views', 0)
        self.replies = topic.get('replies', 0)
        self.favorites = topic.get('favorites', 0)
        self.is_prime = topic.get('is_prime', False)
        self.tags = topic.get('tags', [])
        self.topic = topic

    @cached_property
    def member(self):
        return Member.get_by_username(self.username)

    @cached_property
    def avatar_url(self):
        return self.member.avatar_url

    @cached_property
    def nickname(self):
        return self.member.nickname

    @cached_property
    def last_member(self):
        return Member.get_by_username(self.last_username)

    @cached_property
    def last_nickname(self):
        return self.last_member.nickname

    @property
    def is_locked(self):
        return self.flags & self.LOCKED == self.LOCKED

    @property
    def has_image(self):
        return self.flags & self.IMAGE == self.IMAGE

    @property
    def has_video(self):
        return self.flags & self.VIDEO == self.VIDEO

    @property
    def has_checkin(self):
        return self.flags & self.CHECKIN == self.CHECKIN

    @property
    def total_pages(self):
        return (self.replies + 1) / settings.get('page_size', 50) + 1

    @property
    def tag_names(self):
        tags = []
        for t in self.tags:
            tag = Tag.get_by_id(t)
            if tag:
                tags.append(tag)
        return tags

    @property
    def timestamp(self):
        return time.mktime(datetime.timetuple(self.last_post_date))

    @property
    def json(self):
        return dict(
            topic_id=self.topic_id,
            subject=self.subject,
            username=self.username,
            avatar_url=self.avatar_url,
            post_date=self.post_date.isoformat(),
            last_username=self.last_username,
            last_post_date=self.last_post_date.isoformat(),
            views=self.views,
            replies=self.replies,
            favorites=self.favorites,
            is_prime=self.is_prime
        )

    def save(self):
        self.topic['subject'] = self.subject
        self.topic['flags'] = self.flags
        self.topic['tags'] = self.tags
        self.topic['is_prime'] = self.is_prime
        self.topic['last_username'] = self.last_username
        self.topic['last_post_date'] = self.last_post_date
        self.topic['replies'] = self.replies
        db.topics.save(self.topic)

    @staticmethod
    def get_topic(topic_id):
        topic = db.topics.find_one({'topic_id': topic_id})
        return Topic(topic) if topic else None

    @staticmethod
    def add_views(topic_id):
        db.topics.find_and_modify(
            query={'topic_id': topic_id},
            update={'$inc': {'views': 1}},
            new=True
        )

    @staticmethod
    def edit_flags(topic_id, flags=0, add=True):

        if flags == 0:
            return

        topic = db.topics.find_one({'topic_id': topic_id})
        if topic:
            if add:
                if topic['flags'] & flags != flags:
                    topic['flags'] += flags
                    db.topics.save(topic)
            else:
                if topic['flags'] & flags == flags:
                    topic['flags'] -= flags
                    db.topics.save(topic)

            cache.delete_memoized(Topics.get_topics)


class Topics:

    def __init__(self, topics, total=0):
        self.topics = topics
        self.total = total

    @property
    def as_list(self):
        return self.topics

    @property
    def json(self):
        return dict(
            topics=[topic.json for topic in self.topics],
            total=self.total
        )

    @staticmethod
    @cache.memoize()
    def get_topics(node_id, page=1, size=50):
        if node_id > 0:
            t = db.topics.find({'node_id': node_id}) \
                .sort('last_post_date', DESCENDING) \
                .skip((page - 1) * size) \
                .limit(size)
        else:
            t = db.topics.find() \
                .sort('last_post_date', DESCENDING) \
                .skip((page - 1) * size) \
                .limit(size)

        if t.count(True) == 0:
            return Topics(None, 0)

        return Topics([Topic(topic) for topic in t], t.count())

    @staticmethod
    @cache.memoize()
    def get_by_tag(tag_id, page=1, size=50):
        t = db.topics.find({'tags': {'$in': [tag_id]}})\
            .sort('last_post_date', DESCENDING)\
            .skip((page - 1) * size)\
            .limit(size)
        if t.count(True) == 0:
            return Topics(None, 0)
        return Topics([Topic(topic) for topic in t], t.count())

    @staticmethod
    @cache.memoize()
    def get_primes(node_id, page=1, size=50):
        if node_id > 0:
            t = db.topics.find({'node_id': node_id, 'is_prime': True})\
                .sort('last_post_date', DESCENDING)\
                .skip((page - 1) * size)\
                .limit(size)
        else:
            t = db.topics.find({'is_prime': True}) \
                .sort('last_post_date', DESCENDING) \
                .skip((page - 1) * size) \
                .limit(size)

        if t.count(True) == 0:
            return Topics(None, 0)

        return Topics([Topic(topic) for topic in t], t.count())

    @staticmethod
    @cache.memoize()
    def get_favorites(username, page=1, size=50):

        favorite = Favorite.get_by_username(username)
        if favorite is None:
            return Topics(None, 0)

        t = db.topics.find({'topic_id': {'$in': favorite.posts}}) \
            .sort('last_post_date', DESCENDING) \
            .skip((page - 1) * size) \
            .limit(size)

        if t.count(True) == 0:
            return Topics(None, 0)

        return Topics([Topic(topic) for topic in t], t.count())

    @staticmethod
    def get_by_username(username, page=1, size=50):
        t = db.topics.find({'username': username})\
            .sort('post_date', DESCENDING)\
            .skip((page - 1) * size)\
            .limit(size)

        if t.count(True) == 0:
            return Topics(None, 0)

        return Topics([Topic(topic) for topic in t], t.count())

    @staticmethod
    @cache.memoize(timeout=60 * 60)
    def get_hot_topics(size=10):
        delta = datetime.utcnow() - timedelta(days=7)
        result = db.topics.find({'last_post_date': {'$gte': delta}})\
            .sort([('replies', DESCENDING), ('views', DESCENDING)])\
            .limit(size)

        if result.count(True) == 0:
            return Topics(topics=None, total=0)

        return Topics([Topic(topic) for topic in result], result.count())
