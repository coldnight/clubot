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

from db.status import is_online, set_online
from db.info import add_info, get_info
from db.member import get_members, get_nick
from db.history import add_history

from plugin.util import NOW, get_email, get_logger, paste_code
from plugin.cmd import CommandHandler, AdminCMDHandler
from plugin.city import cityid

from settings import ADMINS, MODES

from thread_pool import ThreadPool

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
        self._thread_pool = ThreadPool(5)
        self._thread_pool.start()         # 启动线程池
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
                if isinstance(to, (str, unicode)):
                    to = JID(to)
                self.logger.debug("send '{0}' to {1!r}".format(body, to))
                typ = stanza.stanza_type
                self._stream.send(self.make_message(to, typ, body))
        else:
            body = NOW() + ' ' + body
            self.logger.debug("store offline message'{0}' for {1!r}"
                                    .format(body, to))
            offline_message = get_info('offline_message', to, '')
            off_msgs = offline_message.split(self.offline_split_symbol)
            if len(off_msgs) >= 10:
                offline_message = self.offline_split_symbol.join(off_msgs[-9:])
            offline_message += self.offline_split_symbol +  body
            add_info('offline_message', offline_message, to)

    def send_offline_message(self, stanza):
        """ 发送离线消息 """
        show = stanza.show
        frm = stanza.from_jid
        offline_message = get_info('offline_message', frm)
        if offline_message:
            off_msgs = offline_message.split(self.offline_split_symbol)
            offline_message = "\n".join(off_msgs)
            offline_message = "离线期间的消息:\n" + offline_message
            m = self.make_message(frm, 'normal', offline_message)
            self._stream.send(m)
            set_online(frm, show)
            add_info('offline_message', '', frm)

    def handle_code(self, stanza, body):
        if body.startswith("```"):
            bodys = body.split("\n")
            typ = bodys[0].strip("`").strip()
            typ = typ if typ else "text"
            codes = "\n".join(bodys[1:]).strip("```")
            return paste_code(stanza.from_jid.bare().as_string(), typ, codes)
        return body

    def send_all_msg(self, stanza, body):
        """ 给除了自己的所有成员发送消息 """
        if cityid(body.strip()):
            return self.send_command(stanza, '-_tq ' + body.strip())
        if body.strip() == 'help':
            return self.send_command(stanza, '-help')
        if body.strip() == 'ping':
            return self.send_command(stanza, '-_ping')
        if body.startswith("```"):
            tmp = self.handle_code(stanza, body)
            if tmp:
                body = tmp
                self.send_back_msg(stanza, body)
        if len(body) > 200:
            url = self.handle_code(stanza, "```\n" + body)
            if url:
                body = u"{0}\n{1}".format(url, body.split("\n")[0][0:50])
                self.send_back_msg(stanza, u"内容过长,贴到:{0}".format(url))
        mode = get_info('mode', stanza.from_jid)
        if mode == 'quiet':
            body = u'你处于{0},请使用-cd命令切换到 {1} '\
                    u'后发言'.format(MODES[mode], MODES['talk'])
            return self.send_back_msg(stanza, body)

        add_history(stanza.from_jid, 'all', body)
        members = get_members(stanza.from_jid)
        current = get_info('channel', stanza.from_jid, 'main')
        members = [m for m in members
                   if get_info('channel', m, 'main') == current]
        self.logger.info("{0} send message {1} to {2!r}"
                            .format(stanza.from_jid, body, members))
        nick = get_nick(stanza.from_jid)
        if body.startswith('/me'):
            body = body.replace('/me', nick + ' ')
        else:
            body = "[{0}] {1}".format(nick, body)
        [self.send_message(stanza, m, body) for m in members]

    def send_back_msg(self, stanza, body):
        """ 发送返回消息 """
        to = stanza.from_jid.bare().as_string()
        typ = stanza.stanza_type
        self._stream.send(self.make_message(to, typ, body))

    def send_sys_msg(self, stanza, body):
        """ 发送系统消息 """
        members = get_members()
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
        self._thread_pool.add_job(target, stanza, body)

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
