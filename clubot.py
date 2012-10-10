#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author : cold night
# Email  : wh_linux@126.com
#
# 2012-10-10 12:00
#     * 使用pyxmpp2重写
#


import logging
import sys, os
import signal
import subprocess
import getpass

from pyxmpp2.jid import JID
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence
from pyxmpp2.client import Client
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.streamevents import AuthorizedEvent, DisconnectedEvent
from pyxmpp2.roster import RosterReceivedEvent
from pyxmpp2.interfaces import XMPPFeatureHandler
from pyxmpp2.interfaces import presence_stanza_handler, message_stanza_handler
from pyxmpp2.ext.version import VersionProvider
from settings import USER,PASSWORD, DEBUG, PIDPATH, LOGPATH, __version__, status
from plugin.db import add_member, del_member, get_member, change_status
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
        settings = XMPPSettings({
                            "software_name": "Clubot",
                            "software_version": __version__,
                            "tls_verify_peer": False,
                            "starttls": True,
                            "ipv6":False
                            })

        settings["password"] = PASSWORD
        version_provider = VersionProvider(settings)
        self.client = Client(my_jid, [self, version_provider], settings)
        self.onlines = []

    def run(self):
        self.client.connect()
        logging.info(u"Connected")
        self.client.run()
        logging.info(u"Looping")

    def disconnect(self):
        self.client.disconnect()
        self.client.run(timeout = 2)

    @presence_stanza_handler("subscribe")
    def handle_presence_subscribe(self, stanza):
        logging.info(u"{0} join us".format(stanza.from_jid))
        frm = stanza.from_jid.bare()
        presence = Presence(to_jid = frm, stanza_type = "subscribe")
        message = Message(to_jid = frm, body = welcome(frm), stanza_type=stanza.stanza_type)
        add_member(frm)
        r =[stanza.make_accept_response(), presence, message]
        r.extend(send_all_msg(stanza, new_member(frm)))
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
        r.extend(send_all_msg(stanza, new_member(frm)))
        return r

    @presence_stanza_handler("unsubscribe")
    def handle_presence_unsubscribe(self, stanza):
        logging.info(u"{0} canceled presence subscription"
                                                    .format(stanza.from_jid))
        presence = Presence(to_jid = stanza.from_jid.bare(),
                                                    stanza_type = "unsubscribe")
        #TODO 离开时昵称应该会发生相应的改变
        message = send_all_msg(stanza, u'{0} 离开群'.format(stanza.from_jid.local))
        del_member(stanza.from_jid.bare())
        r =[stanza.make_accept_response(), presence]
        r.extend(message)
        return r

    @presence_stanza_handler("unsubscribed")
    def handle_presence_unsubscribed(self, stanza):
        logging.info(u"{0!r} acknowledged our subscrption cancelation"
                                                    .format(stanza.from_jid))
        #TODO 离开时昵称应该会发生相应的改变
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
        logging.info(u"{0} send message".format(stanza.from_jid))
        """
        if stanza.subject:
            subject = u"Re: " + stanza.subject
        else:
            subject = None
        msg = Message(stanza_type = stanza.stanza_type,
                        from_jid = stanza.to_jid, to_jid = stanza.from_jid,
                        subject = subject, body = stanza.body,
                        thread = stanza.thread)
                        """
        body = stanza.body
        if not body:
            return True
        if body.startswith('$'):
            msg = send_command(stanza, body)
        else:
            msg = send_all_msg(stanza, body)
        return msg

    @event_handler(DisconnectedEvent)
    def handle_disconnected(self, event):
        return QUIT


    @property
    def roster(self):
        return self.client.roster

    @event_handler(RosterReceivedEvent)
    def handle_roster_received(self, event):
        p = Presence(status=status)
        self.client.stream.send(p)
        ret = [x.jid for x in self.roster if x.subscription == 'both']
        logging.info(' -- roster:{0}'.format(ret))
        for frm in ret:
            if not get_member(frm):
                add_member(frm)

    @event_handler()
    def handle_all(self, event):
        logging.info(u"-- {0}".format(event))

def main():
    global PASSWORD
    if not PASSWORD and args.passwd== 'encrypt':
        PASSWORD = getpass.unix_getpass()
    elif not PASSWORD and args.passwd== 'plain':
        PASSWORD = raw_input("Password: ")
    logging.basicConfig(level=logging.INFO)

    logging.info('main password %s', PASSWORD)
    if DEBUG:
        handler = logging.StreamHandler()
        level = logging.DEBUG
    else:
        level = logging.INFO
        handler = logging.FileHandler(LOGPATH)
        try:
            PID = int(open(PIDPATH, 'r').read())
            os.kill(PID, 9)
        except:
            pass
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            logging.error("Fork #1 failed: %d (%s)", e.errno, e.strerror)
            sys.exit(1)

        os.setsid()
        os.umask(0)

        try:
            pid = os.fork()
            if pid > 0:
                logging.info("Daemon PID %d" , pid)
                pf = open(PIDPATH, 'w')
                pf.write(str(pid))
                pf.close()
                sys.exit(0)
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
    except:
        pass

def restart(signum, stack):
    logging.info('Restart...')
    pwd = subprocess.Popen('echo %s' % PASSWORD, stdin =subprocess.PIPE,
                           stdout = subprocess.PIPE, stderr = subprocess.PIPE,
                           shell = True)
    p = subprocess.Popen(r'python %s --plain&& kill -9 %d'% (
                                                       os.path.split(__file__)[1],
                                                        PID),
                     stdin = pwd.stdout, stdout = subprocess.PIPE,
                     stderr = subprocess.PIPE, shell = True).communicate(pwd.out.read())

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
    parser.add_argument('--plain', action = 'store_const', dest = 'passwd',
                        const = 'plain', default = 'encrypt',
                        help = "Enter password by Plain Text")
    args = parser.parse_args()
    if args.action == 'run':
        main()
    elif args.action == 'restart':
        try:
            PID = int(open(PIDPATH, 'r').read())
            os.kill(PID,1)
        except Exception, e:
            logging.error('Restart failed %s: %s', e.errno, e.strerror)
            logging.info("Try start...")
            main()
            logging.info("done")
    elif args.action == 'stop':
        try:
            PID = int(open(PIDPATH, 'r').read())
            logging.info("Stop the bot")
            os.kill(PID, 9)
        except Exception, e:
            logging.error("Stop failed", e.errno, e.strerror)
