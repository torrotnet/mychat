# coding=UTF-8

from __future__ import print_function

import uuid
import json
from random import choice

import tornado.httpserver
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.gen

from tornado.web import url
import os
import base64
from base import BaseHandler, redis_client, subscriber
from auth import LoginHandler, RegisterHandler, LogoutHandler

try:
    import sockjs.tornado
except:
    print('Please install the sockjs-tornado package to run this demo.')
    exit(1)


class IndexPageHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.redirect("/login")
            return
        name = tornado.escape.xhtml_escape(self.current_user)
        self.render("index.html", title="MyChat", context={"name": name})


class SendMessageHandler(tornado.web.RequestHandler):
    def _send_message(self, channel, msg_type, msg, user=None):
        msg = {'type': msg_type,
               'msg': msg,
               'user': user}
        msg = json.dumps(msg)
        redis_client.publish(channel, msg)

    def post(self):
        message = self.get_argument('message')
        from_user = self.get_argument('from_user')
        to_user = self.get_argument('to_user')
        if to_user:
            self._send_message('private.{}'.format(to_user),
                               'pvt', message, from_user)
            self._send_message('private.{}'.format(from_user),
                               'tvp', message, to_user)
        else:
            self._send_message('broadcast_channel', 'msg', message, from_user)
        self.set_header('Content-Type', 'text/plain')
        self.write('sent: %s' % (message,))


class MessageHandler(sockjs.tornado.SockJSConnection):
    """
    SockJS connection handler.

    Note that there are no "on message" handlers - SockJSSubscriber class
    calls SockJSConnection.broadcast method to transfer messages
    to subscribed clients.
    """
    def _enter_leave_notification(self, msg_type):
        broadcasters = list(subscriber.subscribers['broadcast_channel'].keys())
        message = json.dumps({'type': msg_type,
                              'user': self.user_id,
                              'msg': '',
                              'user_list': [{'id': b.user_id,
                                             'name': b.user_name}
                                            for b in broadcasters]})
        if broadcasters:
            broadcasters[0].broadcast(broadcasters, message)

    def _send_message(self, msg_type, msg, user=None):
        if not user:
            user = self.user_id
        self.send(json.dumps({'type': msg_type,
                              'msg': msg,
                              'user': user}))

    def on_open(self, request):
        # Generate a user ID and name to demonstrate 'private' channels
        self.user_id = str(uuid.uuid4())[:5]
        self.user_name = (
            choice(['John', 'Will', 'Bill', 'Ron', 'Sam', 'Pete']) +
            ' ' +
            choice(['Smith', 'Doe', 'Strong', 'Long', 'Tall', 'Small']))
        # Send it to user
        self._send_message('uid', self.user_name, self.user_id)
        # Subscribe to 'broadcast' and 'private' message channels
        subscriber.subscribe(['broadcast_channel',
                              'private.{}'.format(self.user_id)],
                             self)
        # Send the 'user enters the chat' notification
        self._enter_leave_notification('enters')

    def on_close(self):
        subscriber.unsubscribe('private.{}'.format(self.user_id), self)
        subscriber.unsubscribe('broadcast_channel', self)
        # Send the 'user leaves the chat' notification
        self._enter_leave_notification('leaves')


# application = tornado.web.Application(
#     [(r'/', IndexPageHandler),
#      (r'/send_message', SendMessageHandler),
#      # (r'/register', RegisterHandler)] +
#      ] +
#     sockjs.tornado.SockJSRouter(MessageHandler, '/sockjs').urls)


class Application(tornado.web.Application):
    def __init__(self, **overrides):
        handlers = [
            url(r"/", IndexPageHandler, name='index'),
            url(r"/login", LoginHandler, name='login'),
            url(r"/register", RegisterHandler, name='register'),
            url(r"/logout", LogoutHandler, name='logout'),
        ] + sockjs.tornado.SockJSRouter(MessageHandler, '/sockjs').urls
        settings = {
            'static_path': os.path.join(os.path.dirname(__file__), 'static'),
            'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
            "cookie_secret": base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
            # 'twitter_consumer_key': 'KEY',
            # 'twitter_consumer_secret': 'SECRET',
            # 'facebook_app_id': '180378538760459',
            # 'facebook_secret': '7b82b89eb6aa0d3359e2036e4d1eedf0',
            # 'facebook_registration_redirect_url': 'http://localhost:8888/facebook_login',
            # 'mandrill_key': 'KEY',
            # 'mandrill_url': 'https://mandrillapp.com/api/1.0/',

            # 'xsrf_cookies': False,
            'debug': True,
            'log_file_prefix': "tornado.log",
        }
        tornado.web.Application.__init__(self, handlers, **settings)

application = Application()

if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    print('Demo is running at 0.0.0.0:8888\n'
          'Quit the demo with CONTROL-C')
    tornado.ioloop.IOLoop.instance().start()
