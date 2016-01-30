# coding=UTF-8

import tornado
import bcrypt as bcrypt
from base import BaseHandler
from base import redis_client


class LoginHandler(BaseHandler):
    def get(self):
        # messages = self.application.syncdb.messages.find()
        self.render("login.html", notification=self.get_flash())
        # self.render("login.html")

    def post(self):
        email = self.get_argument("email", "")
        password = self.get_argument("password", "")

        user = redis_client.hgetall(email)
        # user = self.application.syncdb['users'].find_one({'user': email})

        if user and user['password'] and user['password'] == bcrypt.hashpw(password.encode('utf-8'), user['password']):
            self.set_current_user(email)
            # self.set_secure_cookie("user", self.get_argument("name"))
            self.redirect("/")
        else:
            self.set_secure_cookie('flash', "Login incorrect")
            self.redirect(u"/login")

    def set_current_user(self, user):
        print("setting " + user)
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")


class RegisterHandler(LoginHandler):
    def get(self):
        self.render("register.html", next=self.get_argument("next", "/"), notification=self.get_flash())

    def post(self):
        email = self.get_argument("email", "")
        already_taken = redis_client.hgetall(email)
        if already_taken:
            self.set_secure_cookie('flash', "Email already taken")
            self.redirect(u"/register")
        else:
            # Warning bcrypt will block IO loop:
            password = self.get_argument("password", "")
            hashed_pass = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(8))

            if email.find('@') != -1:
                login = email[:email.find('@')]
            else:
                login = email
            user = {'email': email, 'password': hashed_pass, 'login': login}
            redis_client.hmset(email, user)
            self.set_current_user(email)
        self.redirect("/")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(u"/login")
