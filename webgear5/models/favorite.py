from webgear5.settings import db, cache


class Favorite:

    def __init__(self, favorite=None):
        self.id = favorite.get('_id', '')
        self.username = favorite.get('username', '')
        self.posts = favorite.get('posts', [])
        self.favorite = favorite

    @property
    def total(self):
        return len(self.posts)

    def add(self, topic_id):
        if not topic_id in self.posts:
            self.posts.append(topic_id)
            self.__save()
            return 1
        else:
            self.posts.remove(topic_id)
            self.__save()
            return -1

    def __save(self):
        self.favorite['posts'] = self.posts
        db.favorites.save(self.favorite)

    @staticmethod
    @cache.memoize()
    def get_by_username(username):
        favorite = db.favorites.find_one({'username': username})
        if favorite:
            return Favorite(favorite)
        return None

    @staticmethod
    def delete(topic_id):
        for fav in db.favorites.find():
            if topic_id in fav.get('posts', []):
                fav['posts'].remove(topic_id)
                db.favorites.save(fav)
                cache.delete_memoized_verhash(Favorite.get_by_username, fav['username'])
