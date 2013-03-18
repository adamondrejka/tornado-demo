# -*- coding: utf-8 -*-
from bson import ObjectId
import os
from pymongo.mongo_client import MongoClient
from tornado import websocket
import uimodules
import simplejson as json
import tornado.ioloop
import tornado.web

db = MongoClient().tornado_demo

class MessageManager(object):
    connected = []

    def __init__(self, db):
        self.db = db

    # verejne udalosti, preposilaji se na vsechny klienty
    public_events = ['new_topic', 'delete_topic', 'like', 'all_users', 'all_topics']

    # soukrome udalosti, odesilaji se na jednoho konkretniho klienta
    private_events = ['new_message']

    # dalsi povolene udalosti, ktere klient primo neodesila, ale jen prijma
    notify_events = ['user_connected', 'user_disconnected']

    def add_client(self, ws):
        """
        Pridava websocket klienta do globalniho seznamu, pouziva se pri novem spojeni
        """
        self.connected.append(ws)

        for c in self.connected:
            if c != ws:
                self._send_msg(c, 'user_connected', {'username': ws.current_user})

        self._send_msg(c, 'all_users', {'users': [u.current_user for u in self.connected if u != c]})
        self._send_msg(c, 'all_topics', {'topics': self._get_all_topics()})

    def remove_client(self, ws):
        """
        Odebira klienta z globalniho senzmu, pouziva se pri ukonceni spojeni
        """
        self.connected.remove(ws)

        for c in self.connected:
            if c != ws:
                self._send_msg(c, 'user_disconnected', {'username': ws.current_user})

    def process_msg(self, msg, client):
        """
        Zpracovava zpravu z websocket streamu

        Zprava musi byt v JSON ve formatu:

        {
            "event": "...",
            "content" : "..."
        }

        Args:
            msg - zprava
            client - vlsatnik, ktery udalost vyvolal...
        """
        message = self._parse_json(msg)
        event = message.get('event')

        if not event:
            self._send_error(client)

        if event == 'new_topic':
            topic = self.add_topic(message['content'], client)
            topic_json = self._jsonify({'event': 'new_topic', 'content': topic})
            self._send_msg_to_all(topic_json)

        elif event == 'like':
            topic = self.like_topic(message['content'], client)
            topic_json = self._jsonify({'event': 'like', 'content': topic})
            self._send_msg_to_all(topic_json)

        elif event == 'new_message':
            recv = message['content']['reciever']
            for c in self.connected:
                if c.current_user == recv:
                    self._send_msg(c, 'new_message',
                                   {'text': message['content']['text'], 'sender': client.current_user})
                    break

    def add_topic(self, data, client):
        """
        Pridava topic do databaze.

        Data jsou ve formatu:
        {
            "text": "..."
        }
        """
        topics = self.db.topics
        data['author'] = client.current_user
        data['likes'] = 0
        topic_id = topics.insert(data)
        top = topics.find_one({"_id": topic_id})
        top["_id"] = unicode(top["_id"])
        return top

    def add_comment(self, data, client):
        """
        Prida komentar k topicu

        Data jsou v JSON ve formatu:
        {
            "topic_id": "...",
            "text": "..."
        }
        """
        topics = self.db.topics
        topic = topics.find_one({"_id": ObjectId(data['topic_id'])})
        topic['comments'].append({"text": data['text'], 'author': client.current_user})
        topic.save()
        return True

    def like_topic(self, data, client):
        """
        Navysi hodnoti 'libi se' o 1
        """
        res = self.db.topics.update({'_id': ObjectId(data['topic_id'])}, {"$inc": {"likes": 1}})
        new = self.db.topics.find_one({'_id': ObjectId(data['topic_id'])})
        return {'topic_id': unicode(new['_id']), 'likes': new['likes']}

    def _send_error(self, client):
        """
        Odesle chybovou zpravu klientovi
        """
        pass

    def _send_msg_to_all(self, msg):
        for c in self.connected:
            c.write_message(msg)

    def _send_msg(self, client, event, content):
        """
        Odesle zpravu klientovi
        """
        if event in self.public_events or event in self.private_events or event in self.notify_events:
            client.write_message(self._jsonify({'event': event, 'content': content}))

    def _get_all_topics(self):
        topics = self.db.topics
        result = topics.find().sort([("_id", -1)])
        res = []
        for r in result:
            r['_id'] = unicode(r['_id'])
            res.append(r)

        return res

    def _parse_json(self, msg):
        return json.loads(msg)

    def _jsonify(self, msg):
        return json.dumps(msg)


global_msg_manager = MessageManager(db)


class UserMixin():
    @property
    def current_user(self):
        return self.get_secure_cookie('user')


class BaseHandler(UserMixin, tornado.web.RequestHandler):
    pass


class MsgWebSocket(UserMixin, websocket.WebSocketHandler):

    def open(self):
        print "New connection {0}".format(self.current_user)
        self.msg_manager = global_msg_manager
        self.msg_manager.add_client(self)

    def on_message(self, msg):
        """
        Udalost volana pri odeslani klientovi zpravy na server
        """
        self.msg_manager.process_msg(msg, self)

    def on_close(self):
        """
        Funkce je volana po ukonceni spojeni s websocket
        """
        self.msg_manager.remove_client(self)
        print "Closed connection {0}".format(self.current_user)


class LoginHandler(tornado.web.RequestHandler):
    """
    Prihlasovani uzivatelu. Pouze uklada do secure cookie jmeno uzivatele, s kterym se dale pracuje...
    """

    def get(self):
        """
        Zobrazi prihlasovaci obrazovku
        """

        self.render("templates/login.html", msg=None)

    def post(self):
        username = self.get_argument("username", None)
        next = self.get_argument("next", None)

        if username:
            self.set_secure_cookie('user', username)
            if next:
                self.redirect(next)
            else:
                self.redirect('/')
        else:
            self.render("templates/login.html", msg=u"Zadejte uživatelské jméno")


class LogoutHandler(tornado.web.RequestHandler):
    """
    Odhlaseni uzivatele
    """

    def get(self):
        self.clear_cookie('user')
        self.redirect('/')


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render('templates/index.html')


settings = {
    'ui_modules': uimodules,
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    'login_url': '/login/',
    'cookie_secret': 'AFo9pjao;g586a4gASgs4a35(jiaosfasdghsadhdg75'
}

application = tornado.web.Application([
                                          (r'/', MainHandler),
                                          (r'/login/', LoginHandler),
                                          (r'/logout/', LogoutHandler),
                                          (r'/ws/', MsgWebSocket),
                                      ], **settings)

if __name__ == "__main__":
    application.listen(8888)
    print "Listening on 127.0.0.1:8888"
    tornado.ioloop.IOLoop.instance().start()
