#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/25 16:40:36
#   Desc    :   消息处理
#
import time
import threading
from functools import partial
from pyxmpp2.jid import JID
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence

from logics import Logics
from utility import NOW, get_email, get_logger, cityid
from command import CommandHandler, AdminCMDHandler

from settings import ADMINS, MODES, USER


class MessageBus(object):
    """ 消息总线
        用于发送消息和桥接bot和命令
        接收消息分发给群成员
        处理消息命令,指派给相应的命令处理
        供命令处理返回命令或广播命令结果
    """
    def __init__(self, bot_jid, stream):
        self.bot_jid = bot_jid
        self._stream = stream
        self.cmd_handler = CommandHandler(message_bus = self)
        self.admin_cmd_handler = AdminCMDHandler(message_bus = self)
        self.logger = get_logger()
        self.offline_split_symbol = "$_$_$_$"
        return

    def make_message(self, to, typ, body):
        """ 构造消息
            `to` - 接收人 JID
            `typ` - 消息类型
            `body` - 消息主体
        """
        if typ not in ['normal', 'chat', 'groupchat', 'headline']:
            typ = 'chat'
        m = Message(from_jid = self.bot_jid, to_jid = to, stanza_type = typ,
                    body = body)
        return m

    def send_to_admin(self, stanza, body):
        """ 给管理员发送消息 """
        [self.send_message(stanza, admin, body, True) for admin in ADMINS]

    def send_private_msg(self, stanza, to, body):
        """ 发送私信 """
        frm = stanza.from_jid
        nick = Logics.get_one(frm).nick
        body = "[%s 悄悄对你说] %s" % (nick, body)
        self.send_message(stanza, to, body, True)

    def send_message(self, stanza, to, body, log = False):
        """ 发送消息
            `stanza`   - 消息节
            `to`       - 接收人 接收人不在线发送离线消息
            `body`     - 消息主体
            `log`      - 记录历史消息
        """
        if to == USER:
            return
        if log:
            Logics.add_history(stanza.from_jid, to, body)
        if Logics.is_online(to):
            mode = Logics.get_info(to, 'mode').value
            if mode == 'talk' or not mode:
                if isinstance(to, (str, unicode)):
                    to = JID(to)
                self.logger.debug("send '{0}' to {1!r}".format(body, to))
                typ = stanza.stanza_type
                self._stream.send(self.make_message(to, typ, body))
        else:
            body = NOW() + ' ' + body
            self.logger.debug("store offline message'{0}' for {1!r}"
                                    .format(body, to))
            offline_message = Logics.get_info(to, 'offline_message', '').value
            off_msgs = offline_message.split(self.offline_split_symbol)
            if len(off_msgs) >= 10:
                offline_message = self.offline_split_symbol.join(off_msgs[-9:])
            offline_message += self.offline_split_symbol +  body
            Logics.set_info(to, 'offline_message', offline_message)

    def send_offline_message(self, stanza):
        """ 发送离线消息 """
        show = stanza.show
        frm = stanza.from_jid
        offline_message = Logics.get_info(frm, 'offline_message', '').value
        if offline_message:
            off_msgs = offline_message.split(self.offline_split_symbol)
            offline_message = "\n".join(off_msgs)
            offline_message = "离线期间的消息:\n" + offline_message
            if len(off_msgs) == 10:
                offline_message += "\n(仅显示最近10条, 更多历史消息请使用 -old 查看)"
            m = self.make_message(frm, 'chat', offline_message)
            self._stream.send(m)
            Logics.set_online(frm, show)
            Logics.set_info(frm, 'offline_message', '')

    def handle_code(self, stanza, body, nick, back):
        if body.startswith("```"):
            bodys = body.split("\n")
            typ = bodys[0].strip("`").strip()
            typ = typ if typ else ""
            codes = "\n".join(bodys[1:]).strip("```")
            self.cmd_handler._paste(stanza, typ, codes, nick, back)


    def send_all_msg(self, stanza, body):
        """ 给除了自己的所有成员发送消息 """
        nick = Logics.get_one(stanza.from_jid).nick
        if stanza.from_jid.bare().as_string() == USER:
            return
        if cityid(body.strip()):
            return self.send_command(stanza, '-_tq ' + body.strip())
        if body.strip() == 'help':
            return self.send_command(stanza, '-help')
        if body.strip() == 'ping':
            return self.send_command(stanza, '-_ping')
        if body.startswith("```"):
            back = partial(self.send_back_msg, stanza)
            self.handle_code(stanza, body, nick, back)

        mode = Logics.get_info(stanza.from_jid, 'mode').value
        if mode == 'quiet':
            body = u'你处于{0},请使用-cd命令切换到 {1} '\
                    u'后发言'.format(MODES[mode], MODES['talk'])
            return self.send_back_msg(stanza, body)


        if body.startswith(">>>"):
            self.cmd_handler.shell(stanza, body.lstrip(">").lstrip())

        members = Logics.get_members(stanza.from_jid)
        members = [m.email for m in members]

        if len(body) > 200:
            def long_back(body, content):
                nick, url = content.split(" ")
                body = u"{0}\n{1}".format(url, body.split("\n")[0][0:50])
                self.send_back_msg(stanza, u"内容过长,贴到:{0}".format(url))
                self.logger.info("{0} send message {1} to {2!r}"
                                    .format(stanza.from_jid, body, members))
                Logics.add_history(stanza.from_jid, 'all', body)
                [self.send_message(stanza, m, "[{0}] {1}".format(nick, body))
                 for m in members]

            back = partial(long_back, body)
            self.handle_code(stanza, "```\n" + body, nick, back)
            return

        Logics.add_history(stanza.from_jid, 'all', body)
        self.logger.info("{0} send message {1} to {2!r}"
                            .format(stanza.from_jid, body, members))
        if body.startswith('/me'):
            body = body.replace('/me', nick + ' ')
        else:
            if nick != "qxbot":
                body = "[{0}] {1}".format(nick, body)
        [self.send_message(stanza, m, body) for m in members]

    def send_back_msg(self, stanza, body):
        """ 发送返回消息 """
        to = stanza.from_jid.bare().as_string()
        typ = stanza.stanza_type
        self._stream.send(self.make_message(to, typ, body))

    def send_sys_msg(self, stanza, body):
        """ 发送系统消息 """
        members = Logics.get_members()
        members = [m.email for m in members]
        [self.send_message(stanza, m, body) for m in members]

    def send_command(self, stanza,  body):
        """ 处理命令
            为防止阻塞使用线程池处理命令
        """
        email = get_email(stanza.from_jid)
        self.logger.info("{0} run command {1}".format(stanza.from_jid, body))
        if email in ADMINS:
            target = self.admin_cmd_handler._run_cmd
        else:
            target = self.cmd_handler._run_cmd
        target(stanza, body)

    def send_status(self, statustext, to = None):
        if to:
            to_jid = JID(to)
            p = Presence(status=statustext, to_jid = to_jid)
        else:
            p = Presence(status = statustext)
        self._stream.send(p)

    def send_subscribe(self, jid):
        """ 发送订阅 """
        p1 = Presence(from_jid = self.bot_jid, to_jid = jid,
                      stanza_type = 'subscribe')
        p = Presence(from_jid = self.bot_jid, to_jid = jid,
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
