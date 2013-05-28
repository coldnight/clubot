#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author : cold
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
from __future__ import absolute_import

import logging
import sys, os
import traceback

import pyxmpp2
from pyxmpp2.jid import JID
from pyxmpp2.presence import Presence
from pyxmpp2.client import Client
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.streamevents import DisconnectedEvent,ConnectedEvent
from pyxmpp2.roster import RosterReceivedEvent, RosterUpdatedEvent
from pyxmpp2.interfaces import XMPPFeatureHandler
from pyxmpp2.interfaces import presence_stanza_handler, message_stanza_handler
from pyxmpp2.ext.version import VersionProvider

from logics import Logics
from message import MessageBus
#from epoll import EpollMainLoop
from mtornado import TornadoMainLoop
from utility import welcome, new_member, get_logger
from settings import USER,PASSWORD, DEBUG, PIDPATH, STATUS, IMPORT

__version__ = '0.5.0 alpha'

class BotChat(EventHandler, XMPPFeatureHandler):
    trytimes = 0
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
                            "poll_interval": 10,
                            })

        settings["password"] = PASSWORD
        version_provider = VersionProvider(settings)
        self.connected = False
        mainloop = TornadoMainLoop(settings)
        self.client = Client(my_jid, [self, version_provider], settings, mainloop)
        #self.client = Client(my_jid, [self, version_provider], settings)
        self.logger = get_logger()
        self.trytimes = 0
        self.sended = []
        Logics.empty_status()

    def run(self, timeout = None):
        self.client.connect()
        self.client.run(timeout)

    def disconnect(self):
        try:
            self.client.disconnect()
        except:
            pass
        while True:
            try:
                self.run(2)
            except:
                pass
            else:
                break

    @presence_stanza_handler("subscribe")
    def handle_presence_subscribe(self, stanza):
        self.logger.info(u"{0} join us".format(stanza.from_jid))
        frm = stanza.from_jid
        presence = Presence(to_jid = frm, stanza_type = "subscribe")
        Logics.add(frm, None, stanza.show)
        r =[stanza.make_accept_response(), presence]
        if frm not in self.sended:
            self.message_bus.send_sys_msg(stanza, new_member(frm))
            self.message_bus.send_back_msg(stanza, welcome(frm))
            self.sended.append(frm)
        return r

    @presence_stanza_handler("subscribed")
    def handle_presence_subscribed(self, stanza):
        self.logger.info(u"{0!r} accepted our subscription request"
                                                    .format(stanza.from_jid))
        frm = stanza.from_jid
        presence = Presence(to_jid = frm, stanza_type = "subscribe")
        Logics.add(frm, None, stanza.show)
        r =[presence]
        r =[stanza.make_accept_response(), presence]
        if frm not in self.sended:
            self.message_bus.send_sys_msg(stanza, new_member(frm))
            self.message_bus.send_back_msg(stanza, welcome(frm))
            self.sended.append(frm)
        return r

    @presence_stanza_handler("unsubscribe")
    def handle_presence_unsubscribe(self, stanza):
        self.logger.info(u"{0} canceled presence subscription"
                                                    .format(stanza.from_jid))
        presence = Presence(to_jid = stanza.from_jid.bare(),
                                                    stanza_type = "unsubscribe")
        nick = Logics.get_one(stanza.from_jid).nick
        self.message_bus.send_sys_msg(stanza, u'{0} 离开群'.format(nick))
        Logics.drop(stanza.from_jid.bare())
        r =[stanza.make_accept_response(), presence]
        return r

    @presence_stanza_handler("unsubscribed")
    def handle_presence_unsubscribed(self, stanza):
        self.logger.info(u"{0!r} acknowledged our subscrption cancelation"
                                                    .format(stanza.from_jid))
        Logics.drop(stanza.from_jid.bare())
        return True

    @presence_stanza_handler(None)
    def handle_presence_available(self, stanza):
        self.logger.info(r"{0} has been online".format(stanza.from_jid))
        if stanza.from_jid.bare().as_string() != USER:
            Logics.set_online(stanza.from_jid, stanza.show)
        self.message_bus.send_offline_message(stanza)

    @presence_stanza_handler("unavailable")
    def handle_presence_unavailable(self, stanza):
        self.logger.info(r"{0} has been offline".format(stanza.from_jid))
        frm = stanza.from_jid
        if frm.bare().as_string() == USER:
            self.logger.info('bot go to offline')
            self.disconnect()
        Logics.set_offline(frm)

    @message_stanza_handler()
    def handle_message(self, stanza):
        body = stanza.body
        frm = stanza.from_jid.bare().as_string()
        if not body: return True
        self.logger.info("receive message '{0}' from {1}"
                                        .format(body, stanza.from_jid))
        if body.startswith('$') or body.startswith('-'):
            self.message_bus.send_command(stanza, body)
        #elif body.startswith('<') and frm == BRIDGE:
        #    self.message_bus.send_qq_msg(stanza, body)
        else:
            self.message_bus.send_all_msg(stanza, body)
        return True

    @event_handler(DisconnectedEvent)
    def handle_disconnected(self, event):
        return QUIT

    @event_handler(ConnectedEvent)
    def handle_connected(self, event):
        self.message_bus = MessageBus(self.my_jid, self.stream)
        self.connected = True
        BotChat.trytimes = 0

    @property
    def roster(self):
        return self.client.roster

    @property
    def stream(self):
        return self.client.stream

    def invite_member(self, jid):
        logging.info('invite {0}'.format(jid))
        p1 = Presence(from_jid = self.my_jid, to_jid = jid,
                      stanza_type = 'subscribe')
        p = Presence(from_jid = self.my_jid, to_jid = jid,
                     stanza_type = 'subscribed')
        self.stream.send(p)
        self.stream.send(p1)

    @event_handler(RosterUpdatedEvent)
    def handle_roster_update(self, event):
        item = event.item

    @event_handler(RosterReceivedEvent)
    def handle_roster_received(self, event):
        dbstatus = Logics.get_global_info('status').value
        if not dbstatus:
            status = STATUS
        else:
            status = dbstatus
        p = Presence(status=status)
        self.client.stream.send(p)
        ret = [x.jid.bare() for x in self.roster if x.subscription == 'both']
        self.logger.info(' -- roster:{0}'.format(ret))
        members = Logics.get_members()
        members = [m.email for m in members]
        [Logics.add(frm) for frm in ret if not Logics.get_one(frm)]
        if IMPORT:
            [self.invite_member(JID(m)) for m in members if JID(m) not in ret]
        #else:
            #[del_member(JID(m)) for m in members if JID(m) not in ret]

    @event_handler()
    def handle_all(self, event):
        self.logger.info(u"-- {0}".format(event))


def main():
    logger = get_logger()
    if not PASSWORD:
        print >>sys.stderr, 'Please write the password in the settings.py'
        sys.exit(2)
    if not DEBUG:
        try:
            with open(PIDPATH, 'r') as f: os.kill(int(f.read()), 9)
        except: pass
        try:
            pid = os.fork()
            if pid > 0: sys.exit(0)
        except OSError, e:
            logger.error("Fork #1 failed: %d (%s)", e.errno, e.strerror)
            sys.exit(1)
        os.setsid()
        os.umask(0)
        try:
            pid = os.fork()
            if pid > 0:
                with open(PIDPATH, 'w') as f:
                    f.write(str(pid))
                os.waitpid(pid, 0)
                main()
            else:
                bot = BotChat()
                try:
                    bot.run()
                except pyxmpp2.exceptions.SASLAuthenticationFailed:
                    logger.error('Username or Password Error!!!')
                    sys.exit(2)
                except KeyboardInterrupt:
                    logger.info("Exiting...")
                    sys.exit(1)
                except:
                    traceback.print_exc()
                    bot.disconnect()
        except OSError, e:
            logger.error("Daemon started failed: %d (%s)", e.errno, e.strerror)
            os.exit(1)
    else:
        bot = BotChat()
        bot.run()



if __name__ == '__main__':
    logger = get_logger()
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
            logger.info('Restart...')
            PID = int(open(PIDPATH, 'r').read())
            os.kill(PID, 9)
        except Exception, e:
            logger.error('Restart failed %s: %s', e.errno, e.strerror)
            logger.info("Try start...")
            main()
            logger.info("done")
    elif args.action == 'stop':
        try:
            logger.info("Stop the bot")
            PID = int(open(PIDPATH, 'r').read())
            os.kill(PID -1, 9)
            os.kill(PID, 9)
        except Exception, e:
            logger.error("Stop failed line:%d error:%s", e.errno, e.strerror)
