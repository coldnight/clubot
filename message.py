#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/25 16:40:36
#   Desc    :   消息处理
#
from pyxmpp2.jid import JID
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence

from db.status import get_resource, is_online, set_online
from db.info import add_info, get_info
from db.member import get_members, get_nick
from db.history import add_history

from plugin.util import NOW, get_email, get_logger
from plugin.cmd import CommandHandler, AdminCMDHandler
from plugin.city import cityid

from settings import ADMINS

class MessageBus(object):
    def __init__(self, bot_jid, stream):
        self.bot_jid = bot_jid
        self._stream = stream
        self.cmd_handler = CommandHandler(message_bus = self)
        self.admin_cmd_handler = AdminCMDHandler(message_bus = self)
        self.logger = get_logger()
        return

    def make_message(self, to, typ, body):
        """ 构造消息
            `to` - 接收人 JID
            `typ` - 消息类型
            `body` - 消息主体
        """
        if typ not in ['normal', 'chat', 'groupchat', 'headline']:
            typ = 'normal'
        m = Message(from_jid = self.bot_jid, to_jid = to, stanza_type = typ,
                    body = body)
        return m

    def send_to_admin(self, stanza, body):
        """ 给管理员发送消息 """
        [self.send_message(stanza, admin, body, True) for admin in ADMINS]

    def send_private_msg(self, stanza, to, body):
        """ 发送私信 """
        frm = stanza.from_jid
        nick = get_nick(frm)
        body = "[%s 悄悄对你说] %s" % (nick, body)
        self.send_message(stanza, to, body, True)

    def send_message(self, stanza, to, body, log = False):
        """ 发送消息
            `stanza`   - 消息节
            `to`       - 接收人 接收人不在线发送离线消息
            `body`     - 消息主体
            `log`      - 记录历史消息
        """
        if log:
            add_history(stanza.from_jid, to, body)
        if is_online(to):
            mode = get_info('mode', to)
            if mode == 'talk' or not mode:
                resource = get_resource(to)
                tos = [JID(to + "/" + r) for r in resource]
                self.logger.debug("send '{0}' to {1!r}".format(body, tos))
                [self._stream.send(self.make_message(t, stanza.stanza_type,
                                                     body)) for t in tos]
        else:
            body = NOW() + ' ' + body
            self.logger.debug("store offline message'{0}' for {1!r}"
                                    .format(body, to))
            offline_message = get_info('offline_message', to)
            offline_message = offline_message if offline_message else ''
            offline_message += '\n' +  body
            add_info('offline_message', offline_message, to)

    def send_offline_message(self, stanza):
        """ 发送离线消息 """
        show = stanza.show
        frm = stanza.from_jid
        offline_message = get_info('offline_message', frm)
        if offline_message:
            offline_message = "离线期间的消息:\n" + offline_message
            m = self.make_message(frm, 'normal', offline_message)
            self._stream.send(m)
            set_online(frm, show)
            add_info('offline_message', '', frm)

    def send_all_msg(self, stanza, body):
        """ 给除了自己的所有成员发送消息 """
        if cityid(body.strip()):
            return self.send_command(stanza, '-_tq ' + body.strip())
        add_history(stanza.from_jid, 'all', body)
        members = get_members(stanza.from_jid)
        self.logger.info("{0} send message {1} to {2!r}"
                            .format(stanza.from_jid, body, members))
        nick = get_nick(stanza.from_jid)
        body = "[{0}] {1}".format(nick, body)
        [self.send_message(stanza, m, body) for m in members]

    def send_back_msg(self, stanza, body):
        """ 发送返回消息 """
        self.send_message(stanza, stanza.from_jid.bare().as_string(), body)

    def send_sys_msg(self, stanza, body):
        """ 发送系统消息 """
        members = get_members()
        [self.send_message(stanza, m, body) for m in members]

    def send_command(self, stanza,  body):
        email = get_email(stanza.from_jid)
        self.logger.info("{0} run command {1}".format(stanza.from_jid, body))
        if email in ADMINS:
            self.admin_cmd_handler.run_cmd(stanza, body)
        else:
            self.cmd_handler.run_cmd(stanza, body)

    def send_status(self, statustext, to = None):
        if to:
            to_jid = JID(to)
            p = Presence(status=statustext, to_jid = to_jid)
        else:
            p = Presence(status = statustext)
        self._stream.send(p)

    def send_subscribe(self, jid):
        """ 发送订阅 """
        #TODO May be remove resource from jid
        p1 = Presence(from_jid = self.my_jid, to_jid = jid,
                      stanza_type = 'subscribe')
        p = Presence(from_jid = self.my_jid, to_jid = jid,
                     stanza_type = 'subscribed')
        self._stream.send(p)
        self._stream.send(p1)

    def send_unsubscribe(self, jid):
        p1 = Presence(from_jid = self.my_jid, to_jid = jid,
                      stanza_type = 'unsubscribe')
        p = Presence(from_jid = self.my_jid, to_jid = jid,
                     stanza_type = 'unsubscribed')
        self._stream.send(p)
        self._stream.send(p1)
