#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# 生成命令
#
# Author : cold night
# email  : wh_linux@126.com
# 2012-09-27 13:38
#   + 增加$list 时用户是否在线
#   + 增加@功能
#   + 增加@<>为首发私信
#   + 增加查看命令历史
#   + 增加贴代码
#   + 命令增加缓存功能
# 2012-09-28 08:52
#   + 命令生成增加缓存操作
# 2012-10-08 14:16
#   * 修改运行命令方式,方便继承
#   + 添加管理员命令
# 2012-10-29 14:25
#   * 修复部分bug
#   + 添加提交bug
#
# 2012-10-30 14:00
#   * 修改history列表方式
#
# 2012-12-21 15:14
#   * 修改代码结构
#
# 2012-12-24 15:30
#   * 修改ls命令处理方式
#   + 添加cd命令用于模式处理
#   + 添加me命令用于查看自己的信息
#
import re
import time
import traceback

from mysql import get_members, get_nick, get_member, edit_member, add_history
from mysql import is_online, get_history, del_member, get_email
from mysql import add_global_info, get_user_info, get_status
from mysql import user_info_template, add_info, get_info
from settings import __version__, LOGPATH, ADMINS, STATUS, MODES
from util import http_helper, run_code, paste_code, add_commends
from util import get_code_types, Complex, get_logger
from city import cityid

from pyxmpp2.presence import Presence
from pyxmpp2.message import Message
from pyxmpp2.jid import JID

logger = get_logger()

class CommandHandler(object):
    """
        生成命令
        命令对应着方法
        比如敲入 -list 则对应list方法
        需要参数自行从kwargs里提取
        所有命令须返回Message/Presence的实例或实例列表
    """
    _cache = {}
    _modes = MODES
    def ls(self, stanza, *args):
        """列出成员/模式/允许的代码,发送-ls help查看用法"""
        mode = args[0] if len(args) >= 1 else None
        if mode in ['user', 'u', 'users'] or not mode:
            if len(args) > 1:
                nicks = args[1:]
                self._show_nicks(stanza, nicks)
            else:
                self._ls_users(stanza)
        elif mode in ['ct', 'codetype', 'code type', 'codetypes',
                      'code types']:
            self._ct(stanza)
        elif mode in ['m', 'mode', 'modes']:
            body = ''
            for m in self._modes:
                body += "{0}:{1}\n".format(m, self._modes[m])
            self._send_cmd_result(stanza, body.strip())
        else:
            members = get_members()
            nicks = [m.get('nick') for m in members]
            if mode in nicks:
                self._show_nicks(stanza, [mode])
            else:
                body = 'Usage: \n\
                        -ls                   查看所有成员\n\
                        -ls [u|user] [nick]   查看用户\n\
                        -ls nick              查看nick的详细信息\n\
                        -ls [ct|codetype]     查看允许的代码类型\n\
                        -ls [m|mode]          列出所有模式'
                self._send_cmd_result(stanza, body)

    def _ls_users(self, stanza):
        """ 列出成员 """
        frm = stanza.from_jid
        femail = get_email(frm)
        members = get_members()
        body = []
        for m in members:
            email = m.get('email')
            r = '{0} <{1}>'.format(m.get('nick'), m.get('email'))
            if email == femail:
                r = '** ' + r
            elif is_online(email):
                status = get_status(email)
                status = status[0][1] if len(status) >= 1 else None
                r = ' * ' + r
                if status: r +=' ({0})'.format(status)
            else:
                r = '  ' + r
            body.append(r)
        body = sorted(body, key = lambda k:k[1], reverse=True)
        body.insert(0, 'Pythoner Club 所有成员(** 表示你自己, * 表示在线):')
        self._send_cmd_result(stanza, '\n'.join(body))

    def cd(self, stanza, *args):
        """ 进入模式,发送-ls m查看所支持的模式 """
        mode = args[0] if len(args) == 1 else None
        if not mode or mode not in self._modes:
            body = "Usage:\n\
                    -cd MODE    进入MODE模式,使用-ls m查看允许的模式"
        else:
            add_info('mode', mode, stanza.from_jid)
            body = " 你已进入{0}".format(self._modes[mode])

        self._send_cmd_result(stanza, body)

    def trans(self, stanza, *args):
        """中日英翻译,默认英-汉翻译"""
        trans = Complex()
        return self._send_cmd_result(stanza, trans.trans([x for x in args]))


    def _tq(self, stanza, *args):
        """指定城市获取天气"""
        tq = Complex()
        body = tq.tq(''.join([x for x in args]))
        self._send_cmd_result(stanza, body)
        send_all_msg(stanza, self._stream, body)

    def _ping(self, stanza, *args):
        self._send_cmd_result(stanza, 'is ok, I am online')


    def mt(self, stanza, *args):
        """单独给某用户发消息"""
        #TODO Write check online
        if len(args) <= 1: return self.help(stanza, 'msgto')
        nick = args[0]
        receiver = get_member(nick = nick)
        body = ' '.join(args[1:])
        if not receiver:
            self._send_cmd_result(stanza, "%s 用户不存在" % nick)
        else:
            send_to_msg(stanza, self._stream, receiver, body)


    def nick(self, stanza, *args):
        """更改昵称 eg. -nick yournewnickname"""
        if len(args) < 1: return self.help(stanza, 'nick')
        nick = ' '.join(args[0:])
        frm = stanza.from_jid
        oldnick = get_nick(frm)
        r = edit_member(frm, nick = nick)
        if r:
            body = "%s 更改昵称为 %s" % (oldnick, nick)
            send_all_msg(stanza,self._stream, body, True)
            self._send_cmd_result(stanza, u'你的昵称现在的已经已经更改为 {0}'.format(nick))
        else:
            self._send_cmd_result(stanza, '昵称已存在')


    def code(self, stanza, *args):
        """<type> <code> 贴代码,使用-ls ct 查看允许的代码类型"""
        if len(args) <= 1: return self.help(stanza, 'code')
        nick = get_nick(stanza.from_jid)
        typ = args[0]
        codes = add_commends(args[1:], typ, nick)
        codes = ''.join(codes[0:2]) + ' '.join(codes[2:])
        poster = "Pythoner Club: %s" % nick
        r = paste_code(poster,typ, codes)
        if r:
            send_all_msg(stanza, self._stream, r)
            self._send_cmd_result(stanza, r)
        else:
            self._send_cmd_result(stanza, '代码服务异常,通知管理员')

    def py(self, stanza, *args):
        """ 执行Python代码 """
        if len(args) < 1: return self.help(stanza, 'py')
        nick = get_nick(stanza.from_jid)
        code = ' '.join(args)
        result = run_code(code)
        body = u'{0} 执行代码:\n{1}\n'.format(nick, code)
        body += result
        send_all_msg(stanza, self._stream, body, True)
        self._send_cmd_result(stanza, result)

    def _ct(self, stanza, *args):
        """返回允许的代码类型"""
        if self._cache.get('typs'):
            body = self._cache.get('typs')
        else:
            body = get_code_types()
            self._cache.update(typs = body)
        return self._send_cmd_result(stanza, body)


    def it(self, stanza, *args):
        """邀请好友加入 eg. -it <yourfirendemail>"""
        if len(args) < 1:return self.help(stanza, 'invite')
        to = args[0]
        p1 = Presence(from_jid = stanza.to_jid, to_jid = JID(to),
                      stanza_type = 'subscribe')
        p = Presence(from_jid = stanza.to_jid, to_jid = JID(to),
                     stanza_type = 'subscribed')
        self._stream.send(p1)
        self._stream.send(p)


    def help(self, stanza, *args):
        """显示帮助"""
        if args:
            func = self._get_cmd(args[0])
            if func:
                body ="-{0} : {1}".format(args[0], func.__doc__)
            else:
                body = "-{0} : command unknow" .format(args[0])
        else:
            body = []
            funcs = self._get_cmd()
            for f in funcs:
                r = "-%s\t%s" % (f.get('name'), f.get('func').__doc__)
                body.append(r)
            body = sorted(body, key=lambda k:k[1])
            body = '\n'.join(body)
        self._send_cmd_result(stanza, body)


    def history(self, stanza, *args):
        """显示聊天历史"""
        sef = stanza.from_jid
        if args:
            self._send_cmd_result(stanza, get_history(sef, *args))
        else:
            self._send_cmd_result(stanza, get_history(sef))

    def bug(self, stanza, *args):
        """提交bug(请详细描述bug,比如使用什么命令,返回了什么)"""
        bugcontent = '\n'.join(args)
        if not bugcontent: return self._send_cmd_result(stanza, u'请填写bug内容')

        email = stanza.from_jid.bare().as_string()
        username = get_nick(stanza.from_jid)
        url = "http://www.linuxzen.com/wp-comments-post.php"
        param = dict(author=username, email=email, comment=bugcontent,
                    akismet_comment_nonce="7525bb940f", comment_post_ID='412',
                    comment_parent=0, submit=u'发表评论', url='')
        get_url = lambda res:res.url
        try:
            http_helper(url=url,param = param, callback=get_url)
            self._send_cmd_result(stanza, u'bug 提交成功,感谢支持!!')
        except:
            self._send_cmd_result(stanza, u'bug 提交失败,稍候再试,感谢支持!!')

    def _show_nicks(self, stanza, nicks):
        """ 显示所有昵称的信息 """
        emails = [get_member(nick = n) for n in nicks]
        infos = [self._whois(e) for e in emails]
        body = '\n\n'.join(infos)
        self._send_cmd_result(stanza, body)

    def _whois(self, frm):
        result = get_user_info(frm)
        body = user_info_template.substitute(result)
        return body

    def me(self, stanza, *args):
        """ 查看自己的详细信息 """
        body = self._whois(stanza.from_jid)
        self._send_cmd_result(stanza, body)

    def version(self, stanza, *args):
        """显示版本信息"""
        author = ['cold(wh_linux@126.com)',
                    'eleven.i386(eleven.i386@gmail.com)',]
        body = "Version %s\nAuthors\n\t%s\n" % (__version__,
                                                '\n\t'.join(author))
        body += "\nhttps://github.com/coldnight/clubot"
        return self._send_cmd_result(stanza, body)


    def _set_cache(self, key, data, expires = None):
        """设置缓存 expires(秒) 设置过期时间None为永不过期"""
        if expires:
            self._cache[key] = {}
            self._cache[key]['data'] = data
            self._cache[key]['expires'] = expires
            self._cache[key]['time'] = time.time()
        else:
            self._cache[key]['data'] = data


    def _get_cache(self, key):
        """获取缓存"""
        if not self._cache.has_key(key): return None
        if self._cache[key].has_key('expires'):
            expires = self._cache[key]['expires']
            time = self._cache[key]['time']
            if (time.time() - time) > expires:
                return None
            else:
                return self._cache[key].get('data')
        else:
            return self._cache[key].get('data')


    def _send_cmd_result(self, stanza, body):
        """返回命令结果"""
        frm = stanza.from_jid
        email = get_email(frm)
        send_msg(stanza, self._stream, email, body)


    def _get_cmd(self, name = None):
        if name:
            command = getattr(self, name)
        else:
            command = [{'name':k, 'func':getattr(self, k)}
                       for k in dir(self) if not k.startswith('_')]
        return command


    def __getattr__(self, name):
        return self.help


    def _parse_args(self, cmd):
        cmd = cmd.strip()
        splitbody = cmd.split('\n')
        if len(splitbody) >= 2:
            cmdline = (splitbody[0], '\n'.join(splitbody[1:]))
        else:
            cmdline= splitbody
        tmp = list(cmdline)
        cmdline = tmp[0].split(' ') + tmp[1:]
        return cmdline[0], cmdline[1:]

    def _run_cmd(self, stanza, stream, cmd, pre):
        """获取命令"""
        c, args = self._parse_args(cmd)
        email = get_email(stanza.from_jid)
        self._stream = stream
        cmds = [v.get('name') for v in self._get_cmd()]
        if c not in cmds:
            send_all_msg(stanza, stream, pre + cmd)
            return
        try:
            logger.info('%s run cmd %s', email, c)
            m =getattr(self, c)(stanza, *args)
        except Exception as e:
            logger.warning(e.message)
            errorinfo = traceback.format_exc()
            body = u'{0} run command {1} happend an error:\
                    {2}'.format(get_nick(email), c, errorinfo)
            [send_to_msg(stanza, self._stream, admin, body)
             for admin in ADMINS]
            self._send_cmd_result(stanza, c + ' 命令异常,已通知管理员')
            return

        return m


class AdminCMDHandle(CommandHandler):
    """管理员命令"""
    def log(self, stanza, *args):
        """查看日志"""
        lf = open(LOGPATH)
        lines = lf.readlines()
        lines.append('\ntotal lines: %d' % len(lines))
        if len(args) == 2:
            start = int(args[0]) * int(args[1])
            end = start + int(args[1])
        elif len(args) == 1:
            start = int(args[0]) * 10
            end = start + 10
        else:
            start = 1
            end = 10
        body = ''.join(lines[-end:-start]) if len(lines) > 10 else ''.join(lines)

        return self._send_cmd_result(stanza, body)


    def rm(self, stanza, *args):
        """剔除用户"""
        #XXX 没有效果
        emails = [get_member(nick = n) for n in args]
        if len(emails) < 1: return self.help(stanza, 'rm')
        for e in emails:
            jid = JID(e)
            self._stream.send(Presence(to_jid = jid, stanza_type='unsubscribe'))
            del_member(jid)

    def cs(self, stanza, *args):
        """ 更改状态 """
        if args:
            status = ' '.join(args)
        else:
            status = STATUS
        add_global_info('status', status)
        p = Presence(status = status)
        self._stream.send(p)


cmd = CommandHandler()
admincmd = AdminCMDHandle()
run_cmd = cmd._run_cmd
admin_run_cmd = admincmd._run_cmd


def send_command(stanza, stream, body):
    logger.info(u"{0} send command: {1}".format(stanza.from_jid, body))
    cmd = body[1:]
    pre = body[0]
    email = get_email(stanza.from_jid)
    if email in ADMINS:
        admin_run_cmd(stanza, stream, cmd, pre)
    else:
        run_cmd(stanza, stream, cmd, pre)


def send_msg(stanza, stream, to_email, body):
    typ = stanza.stanza_type
    if typ not in ['normal', 'chat', 'groupchat', 'headline']:
        typ = 'normal'
    m=Message(to_jid=JID(to_email),stanza_type=typ,body=body)
    stream.send(m)


def send_at_msg(stanza, stream, body, nick):
    """发送@消息"""
    r = re.findall(r'@<(.*?)>', body)
    mem = [get_member(nick=n) for n in r if get_member(nick = n)]
    if mem and body.startswith('@<'):
        b = re.sub(r'^@<.*?>', '', body)
        send_to_msg(stanza, stream, mem[0], b)
        return True
    elif mem:
        b = '%s 提到了你说: %s' % (nick, body)
        [send_to_msg(stanza, stream, to, b) for to in mem]

def send_all_msg(stanza, stream, body, system=False):
    """
    发送所有消息
    - `stanza` : 来源消息结
    - `stream` : xmpp流 (added at 2012-10-29)
    - `body`   : 发送消息主体
    - `system` : 是否为系统消息 ( added at 2012-10-29)
    """
    frm = stanza.from_jid
    mode = get_info('mode', frm)
    if mode and mode == 'quiet':
        body = "你现在在安静模式下,如要发送消息请使用-cd命令切换到聊天模式"
        send_msg(stanza, stream, frm.bare().as_string(), body)
        return
    nick = get_nick(frm)
    tos = get_members(frm)
    tos = [to for to in tos
           if get_info('mode', to) == 'talk' or not get_info('mode', to)]
    add_history(frm, 'all', body)
    logger.info(u"{0} send message: {1}".format(stanza.from_jid, body))
    if cityid(body.strip()):
        return send_command(stanza, stream, '-_tq {0}'.format(body))
    if '@' in body:
        isreturn = send_at_msg(stanza, stream, body, nick)
        if isreturn:
            return
    elif body.strip() == 'help':
        return send_command(stanza, stream, '-help')
    elif body.strip() == 'ping':
        return send_command(stanza, stream, '-_ping')
    body = "{0}".format(body) if system else "[%s] %s" % (nick, body)
    [send_msg(stanza, stream, to, body) for to in tos]


def send_to_msg(stanza, stream, to, body):
    frm = stanza.from_jid
    nick = get_nick(frm)
    add_history(frm, to, body)
    body = "[%s 悄悄对你说] %s" % (nick, body)
    send_msg(stanza, stream, to, body)
