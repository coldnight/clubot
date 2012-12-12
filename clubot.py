#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author : cold night
# Email  : wh_linux@126.com
#
# 2012-10-10 12:00
#     * 使用pyxmpp2重写
# 2012-10-29 14:25
#     * 修复自动下线和发送系统消息的bug
#     * 修复用户离群的bug
#     + 添加多线程处理消息
# 2012-10-30 16:00
#     + 添加连接之前清除状态表
# 2012-11-19 14:00
#     * 修复断开自动重启
#


import logging
import sys, os
import random
import signal
import subprocess
import threading

from pyxmpp2.jid import JID
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence
from pyxmpp2.client import Client
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.stanza import Stanza
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.streamevents import DisconnectedEvent
from pyxmpp2.roster import RosterReceivedEvent
from pyxmpp2.interfaces import XMPPFeatureHandler
from pyxmpp2.interfaces import presence_stanza_handler, message_stanza_handler
from pyxmpp2.ext.version import VersionProvider
from settings import USER,PASSWORD, DEBUG, PIDPATH, __version__, status, IMPORT
from plugin.db import add_member, del_member, get_member, change_status, get_nick
from plugin.db import empty_status, get_members, handler, level
from plugin.cmd import send_all_msg, send_command



def welcome(frm):
    r = u"欢迎加入我们\n你的昵称是{0}\n可以使用{1}更改你的昵称\n"
    r += u"可以使用help查看帮助"
    r = r.format(frm.local, "$nick")
    return r

def new_member(frm):
    return u"{0} 加入群".format(frm.local)

class BotChat(EventHandler, XMPPFeatureHandler):
    def __init__(self):
        my_jid = JID(USER+'/Bot')
        self.my_jid = my_jid
        settings = XMPPSettings({
                            "software_name": "Clubot",
                            "software_version": __version__,
                            "software_os": "Linux",
                            "tls_verify_peer": False,
                            "starttls": True,
                            "ipv6":False,
                            })

        settings["password"] = PASSWORD
        version_provider = VersionProvider(settings)
        self.do_quit = False
        self.client = Client(my_jid, [self, version_provider], settings)
        self.stanza = Stanza(
        empty_status()

    def run(self):
        self.client.connect()
        logging.info(u"Connected")
        self.client.run()
        logging.info(u"Looping")

    def disconnect(self):
        self.do_quit = True
        self.client.disconnect()
        logging.warning('reconnect....')
        with open(PIDPATH, 'r') as f: os.kill(int(f.read()), 1)

    @presence_stanza_handler("subscribe")
    def handle_presence_subscribe(self, stanza):
        logging.info(u"{0} join us".format(stanza.from_jid))
        frm = stanza.from_jid.bare()
        presence = Presence(to_jid = frm, stanza_type = "subscribe")
        message = Message(to_jid = frm, body = welcome(frm), stanza_type=stanza.stanza_type)
        add_member(frm)
        r =[stanza.make_accept_response(), presence, message]
        send_all_msg(stanza, self.stream, new_member(frm), True)
        return r

    @presence_stanza_handler("subscribed")
    def handle_presence_subscribed(self, stanza):
        logging.info(u"{0!r} accepted our subscription request"
                                                    .format(stanza.from_jid))
        frm = stanza.from_jid.bare()
        presence = Presence(to_jid = frm, stanza_type = "subscribe")
        message = Message(to_jid = frm, body = welcome(frm))
        add_member(frm)
        r =[presence, message]
        add_member(frm)
        send_all_msg(stanza, self.stream, new_member(frm), True)
        return r

    @presence_stanza_handler("unsubscribe")
    def handle_presence_unsubscribe(self, stanza):
        logging.info(u"{0} canceled presence subscription"
                                                    .format(stanza.from_jid))
        presence = Presence(to_jid = stanza.from_jid.bare(),
                                                    stanza_type = "unsubscribe")
        nick = get_nick(stanza.from_jid)
        send_all_msg(stanza,self.stream, u'{0} 离开群'.format(nick), True)
        del_member(stanza.from_jid.bare())
        r =[stanza.make_accept_response(), presence]
        return r

    @presence_stanza_handler("unsubscribed")
    def handle_presence_unsubscribed(self, stanza):
        logging.info(u"{0!r} acknowledged our subscrption cancelation"
                                                    .format(stanza.from_jid))
        del_member(stanza.from_jid.bare())
        return True

    @presence_stanza_handler(None)
    def handle_presence_available(self, stanza):
        logging.info(r"{0} has been online".format(stanza.from_jid))
        show = stanza.show
        frm = stanza.from_jid
        change_status(frm, 1, show)

    @presence_stanza_handler("unavailable")
    def handle_presence_unavailable(self, stanza):
        logging.info(r"{0} has been offline".format(stanza.from_jid))
        show = stanza.show
        frm = stanza.from_jid
        change_status(frm, 0, show)

    @message_stanza_handler()
    def handle_message(self, stanza):
        body = stanza.body
        name = stanza.from_jid.bare().as_string()
        if not body: return True
        if body.startswith('$') or body.startswith('-'):
            target, name = send_command, '{0}_run_cmd_{1}'.format(name, random.random())
        else:
            target, name = send_all_msg, '{0}_send_msg_{1}'.format(name, random.random())
        t = threading.Thread(name=name,target=target, args=(stanza, self.stream, body))
        t.setDaemon(True)
        t.start()
        return True

    @event_handler(DisconnectedEvent)
    def handle_disconnected(self, event):
       main()

    @property
    def roster(self):
        return self.client.roster

    @property
    def stream(self):
        return self.client.stream

    def invite_member(self, jid):
        p1 = Presence(from_jid = self.my_jid, to_jid = jid,
                      stanza_type = 'subscribe')
        p = Presence(from_jid = self.my_jid, to_jid = jid,
                     stanza_type = 'subscribed')
        self.stream.send(p)
        self.stream.send(p1)

    @event_handler(RosterReceivedEvent)
    def handle_roster_received(self, event):
        p = Presence(status=status)
        self.client.stream.send(p)
        ret = [x.jid.bare() for x in self.roster if x.subscription == 'both']
        logging.info(' -- roster:{0}'.format(ret))
        members = [m.get('email') for m in get_members()]
        [add_member(frm) for frm in ret if not get_member(frm)]
        if IMPORT:
            [self.invite_member(JID(m)) for m in members if JID(m) not in ret]
        else:
            [del_member(JID(m)) for m in members if JID(m) not in ret]

    @event_handler()
    def handle_all(self, event):
        logging.info(u"-- {0}".format(event))

    def send_msg(self, msg, to=None):
        if to:
            if isinstance(to, (list, tuple)):
                tos = to
            elif isinstance(to, (str, unicode)):
                tos = [to]
        else:
            tos = get_members(self.my_jid)
        msgs = [Message(to_jid=JID(to),
                        stanza_type='normal',
                        body=msg) for to in tos]
        [self.stream.send(msg) for msg in msgs]

def main():
    if not PASSWORD:
        print u'Error:Please write the password in the settings.py'
        sys.exit(2)
    if not DEBUG:
        try:
            with open(PIDPATH, 'r') as f: os.kill(int(f.read()), 9)
        except: pass
        try:
            pid = os.fork()
            if pid > 0: sys.exit(0)
        except OSError, e:
            logging.error("Fork #1 failed: %d (%s)", e.errno, e.strerror)
            sys.exit(1)
        os.setsid()
        os.umask(0)
        try:
            pid = os.fork()
            if pid > 0:
                logging.info("Daemon PID %d" , pid)
                with open(PIDPATH, 'w') as f: f.write(str(pid))
                sys.exit(0)
            else:
                #TODO
                pass
        except OSError, e:
            logging.error("Daemon started failed: %d (%s)", e.errno, e.strerror)
            os.exit(1)

    handler.setLevel(level)
    for logger in ("pyxmpp2.IN", "pyxmpp2.OUT"):
        logger = logging.getLogger(logger)
        logger.setLevel(level)
        logger.addHandler(handler)
        logger.propagate = False
    bot = BotChat()
    try:
        bot.run()
    except Exception as ex:
        logging.error(ex.message)


def restart(signum, stack):
    logging.info('Restart...')
    PID = int(open(PIDPATH, 'r').read())
    pf = os.path.join(os.path.dirname(__file__), __file__)
    cmd = r'kill -9 {0} && python {1} '.format(PID, pf)
    print cmd
    subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                     stderr = subprocess.PIPE, shell = True)

signal.signal(signal.SIGHUP, restart)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description = "Pythoner Club group bot")
    parser.add_argument('--restart', action = 'store_const', dest = 'action',
                        const  = 'restart', default='run',
                        help = 'Restart the bot')
    parser.add_argument('--stop', action = 'store_const', dest = 'action',
                        const = 'stop', default='run',
                        help = 'Stop the bot')
    args = parser.parse_args()
    if args.action == 'run': main()
    elif args.action == 'restart':
        try:
            with open(PIDPATH, 'r') as f: os.kill(int(f.read()), 1)
        except Exception, e:
            logging.error('Restart failed %s: %s', e.errno, e.strerror)
            logging.info("Try start...")
            main()
            logging.info("done")
    elif args.action == 'stop':
        try:
            logging.info("Stop the bot")
            with open(PIDPATH, 'r') as f: os.kill(int(f.read()), 9)
        except Exception, e:
            logging.error("Stop failed line:%d error:%s", e.errno, e.strerror)
