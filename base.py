# coding=UTF-8

import tornado

import redis
import tornadoredis
import tornadoredis.pubsub

# Use the synchronous redis client to publish messages to a channel
redis_client = redis.Redis()
# Create the tornadoredis.Client instance
# and use it for redis channel subscriptions
subscriber = tornadoredis.pubsub.SockJSSubscriber(tornadoredis.Client())


class BaseHandler(tornado.web.RequestHandler):
    def get_login_url(self):
        return u"/login"

    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get_flash(self):
        flash = self.get_secure_cookie('flash')
        self.clear_cookie('flash')
        return flash

