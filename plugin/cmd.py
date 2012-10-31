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


import re
import time
from db import get_members
from db import get_nick, get_member
from db import edit_member
from db import add_history
from db import is_online
from db import get_history
from db import logger
from db import del_member
from db import get_email
from db import get_status
from pyxmpp2.message import Message
from pyxmpp2.jid import JID
from pyxmpp2.presence import Presence
from fanyi import Complex
from settings import __version__
from settings import USER
from settings import LOGPATH
from settings import ADMINS
from city import cityid





def http_helper(url, param = None, callback=None):
    import urllib, urllib2
    if param:
        data = urllib.urlencode(param)
        req =urllib2.Request(url,data)
    else:
        req = urllib2.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:14.0) Gecko/20100101 Firefox/14.0.1")
    res = urllib2.urlopen(req)

    if callback:
        result = callback(res)
    else:
        result =  res.read()
    return result


def _get_code_types():
    """获取贴代码支持的类型"""
    purl = "http://paste.linuxzen.com/"
    def handle(res):
        r = re.compile(r'<option\s+value="(.*?)".*?>(.*?)</option>')
        result = []
        for line in res.readlines():
            if '<option' not in line: continue
            t = dict()
            t['key'], t['value'] = r.findall(line)[0]
            result.append(t)
        return result
    try:
        result = http_helper(purl, callback=handle)
        import string
        t = string.Template("""$key : $value  """)
        r = [t.substitute(v) for v in result]
        result = '\n'.join(r)
    except:
        result = u'代码服务异常,请通知管理员稍候再试'
    return result


def paste_code(poster, typ, codes):
    param = {'class':typ}
    param.update(poster=poster, code = codes, paste="发送")
    purl = "http://paste.linuxzen.com/"

    get_url = lambda res:res.url
    try:
        url = http_helper(purl, param, get_url)
    except:
        return False
    if url == purl:
        return False
    else:
        return url


def _add_commends(codes, typ, nick):
    commends = {"actionscript": "// ", "actionscript-french" : "// ",
                "ada" : "-- ","apache" : "# ","applescript" : "- ",
                "asm" : "; ","asp" : "// ",  "autoit" : "; ","bash" : "# ",
                "blitzbasic" : "' ","c ":"// ","c_mac" : "// ",
                "cpp" :" // ","csharp" : "// ","css" : ["/* ", " */"],
                "freebasic" : "' ","html4strict" : ["<!-- ", " -->"],
                "java" : "//  ","java5" : "//  ","javascript" : "//  ",
                "lisp" : ";; ","lua" : "--  ","mysql" : "--  ",
                "objc" : "// ","perl" : "# ","php" : "// ",
                "php-brief" : "//  ","python" : "# ","qbasic" : "' ",
                "robots" : "# ","ruby" : "#","sql" : "--  ",
                "tsql" : "-- ","vb" : "'  ","vbnet" : "//  ", "xml":["<!--", "-->"],
                "vim":'"'
               }
    codes  = list(codes)
    symbol = commends.get(typ, '// ')
    if isinstance(symbol, list):
        c = "%s 由Pythoner Club 的 %s 提交\n 欢迎加入我们讨论技术: \
            \n\t使用gtalk添加%s %s\n" % (symbol[0], nick, USER, symbol[1])
    else:
        c = "%s 由Pythoner Club 的 %s 提交\n%s 欢迎加入我们讨论技术: \
            \n%s\t使用gtalk添加%s\n" % (symbol, nick, symbol, symbol, USER)
    c += "#\n#\n####### Code Start #####################\n"
    codes.insert(0, c)

    return codes



class CommandHandler(object):
    """
        生成命令
        命令对应着方法
        比如敲入 -list 则对应list方法
        命令具有统一接收stanza固定参数和变参*args,
        需要参数自行从kargs里提取
        所有命令须返回Message/Presence的实例或实例列表
    """
    _cache = {}
    def list(self, stanza, *args):
        """列出所有成员"""
        frm = stanza.from_jid
        femail = get_email(frm)
        members = get_members()
        body = []
        for m in members:
            email = m.get('email')
            r = '%s <%s>' % (m.get('nick'), m.get('email'))
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
        return self._send_cmd_result(stanza, '\n'.join(body))

    def trans(self, stanza, *args):
        """中日英翻译,默认英-汉翻译,eg $trans zh-en 中文,$trans ja-zh 死ぬ行く"""
        trans = Complex()
        return self._send_cmd_result(stanza, trans.trans([x for x in args]))

    def _tq(self, stanza, *args):
        """指定城市获取天气, eg. $tq 广州"""
        tq = Complex()
        body = tq.tq(''.join([x for x in args]))
        self._send_cmd_result(stanza, body)
        send_all_msg(stanza, self._stream, body)

    def msgto(self, stanza, *args):
        """单独给某用户发消息 eg $msgto nick hello(给nick发送hello) 也可以使用@<nick> 消息"""
        if len(args) > 1:
            nick = args[0]
            receiver = get_member(nick = nick)
            body = ' '.join(args[1:])
            if not receiver:
                m  = self._send_cmd_result(stanza, "%s 用户不存在" % nick)
            else:
                m = send_to_msg(stanza, self._stream, receiver, body)
        else:
            m = self.help(stanza, 'mgsto')

        return m


    def nick(self, stanza, *args):
        """更改昵称 eg. $nick yournewnickname"""
        if len(args) >= 1:
            nick = ' '.join(args[0:])
            frm = stanza.from_jid
            oldnick = get_nick(frm)
            r = edit_member(frm, nick = nick)
            if r:
                body = "%s 更改昵称为 %s" % (oldnick, nick)
                send_all_msg(stanza,self._stream, body, True)
                self._send_cmd_result(stanza, u'你的现在的已经已经更改为 {0}'.format(nick))
            else:
                self._send_cmd_result(stanza, '昵称已存在')
        else:
            self.help(stanza, 'nick')


    def code(self, stanza, *args):
        """<type> <code> 贴代码,可以使用$codetypes查看允许的代码类型"""
        if len(args) > 1:
            nick = get_nick(stanza.from_jid)
            typ = args[0]
            codes = _add_commends(args[1:], typ, nick)
            codes = ''.join(codes[0:2]) + ' '.join(codes[2:])
            poster = "Pythoner Club: %s" % nick
            r = paste_code(poster,typ, codes)
            if r:
                m = send_all_msg(stanza, self._stream, r)
                mc = self._send_cmd_result(stanza, r)
                m.append(mc)
            else:
                m = self._send_cmd_result(stanza, 'something wrong')
        else:
            m = self.help(stanza, 'code')
        return m




    def codetypes(self, stanza, *args):
        """返回有效的贴代码的类型"""
        if self._cache.get('typs'):
            body = self._cache.get('typs')
        else:
            body = _get_code_types()
            self._cache.update(typs = body)
        return self._send_cmd_result(stanza, body)


    def invite(self, stanza, *args):
        """邀请好友加入 eg. $invite <yourfirendemail>"""
        if len(args) >= 1:
            to = args[0]
            p1 = Presence(from_jid = stanza.to_jid,
                         to_jid = JID(to),
                         stanza_type = 'subscribe')
            p = Presence(from_jid = stanza.to_jid,
                         to_jid = JID(to),
                         stanza_type = 'subscribed')
            self._stream.send(p1)
            self._stream.send(p)
        else:
            return self.help(stanza, 'invite')

    def help(self, stanza, *args):
        """显示帮助"""
        if args:
            func = self._get_cmd(args[0])
            if func:
                body ="$%s : %s" % (args[0], func.__doc__)
            else:
                body = "$%s : command unknow" % args[0]
        else:
            body = []
            funcs = self._get_cmd()
            for f in funcs:
                r = "$%s  %s" % (f.get('name'), f.get('func').__doc__)
                body.append(r)
            body = sorted(body, key=lambda k:k[1])
            body = '\n'.join(body)
        return self._send_cmd_result(stanza, body)


    def history(self, stanza, *args):
        """<from> <index> <size> 显示聊天历史"""
        sef = stanza.from_jid
        if args:
            return self._send_cmd_result(stanza, get_history(sef, *args))
        else:
            return self._send_cmd_result(stanza, get_history(sef))

    def bug(self, stanza, *args):
        """提交bug(请详细描述bug,比如使用什么命令,返回了什么)"""
        bugcontent = '\n'.join(args)
        if not bugcontent:
            self._send_cmd_result(stanza, u'请填写bug内容')
            return
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



    def version(self, stanza, *args):
        """显示版本信息"""
        author = ['cold night(wh_linux@126.com)',
                    'eleven.i386(eleven.i386@gmail.com)',]
        body = "Version %s\nAuthors\n\t%s\n" % (__version__, '\n\t'.join(author))
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
            r = getattr(self, name)
        else:
            r = [{'name':k, 'func':getattr(self, k)} for k in dir(self) if not k.startswith('_')]
        return r


    def __getattr__(self, name):
        return self.help


    def _parse_args(self, cmd):
        args = []
        c = ''
        splitbody = cmd.split('\n')
        if len(splitbody) >= 2:
            cmdline = splitbody[0]
            body = '\n'.join(splitbody[1:])
        else:
            if len(splitbody) == 1:
                cmdline = splitbody[0]
                body = None
            else:
                cmdline,body = splitbody

        for i, v in enumerate(cmdline.split(' ')):
            if i == 0:
                c = v
            else:
                args.append(v)
        if body:args.append(body)
        return c, args

    def _run_cmd(self, stanza, stream, cmd):
        """获取命令"""
        c, args = self._parse_args(cmd)
        email = get_email(stanza.from_jid)
        self._stream = stream
        try:
            logger.info('%s run cmd %s', email, c)
            m =getattr(self, c)(stanza, *args)
        except Exception as e:
            logger.warning(e.message)
            body = u'{0} run command {1} happend an error: {2}'.format(get_nick(email), c, e.message)
            [send_to_msg(stanza, self._stream, admin, body) for admin in ADMINS]

        return m


class AdminCMDHandle(CommandHandler):
    """管理员命令"""
    def log(self, stanza, *args):
        """查看日志($log <page> <size>)"""
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
        if len(lines) > 10:
            body = ''.join(lines[-end:-start])
        else:
            body = ''.join(lines)

        return self._send_cmd_result(stanza, body)


    def rm(self, stanza, *args):
        """剔除用户($rm nick1 nick2 nick3...)"""
        #TODO 没有效果
        emails = [get_member(nick = n) for n in args]
        if emails >= 1:
            for e in emails:
                jid = JID(e)
                self._stream.send(Presence(to_jid = jid, stanza_type='unsubscribe'))
                del_member(jid)
        else:
            self.help(stanza, 'rm')


run_cmd = CommandHandler()._run_cmd
admin_run_cmd = AdminCMDHandle()._run_cmd



def send_command(stanza, stream, body):
    cmd = body[1:]
    email = get_email(stanza.from_jid)
    if email in ADMINS:
        admin_run_cmd(stanza, stream, cmd)
    else:
        run_cmd(stanza, stream, cmd)


def send_msg(stanza, stream, to_email, body):
    typ = stanza.stanza_type
    if typ not in ['normal', 'chat', 'groupchat', 'headline']:
        typ = 'normal'
    m=Message(to_jid=JID(to_email),stanza_type=typ,body=body)
    stream.send(m)

def send_all_msg(stanza, stream, body, system=False):
    """
    发送所有消息
    - `stanza` : 来源消息结
    - `stream` : xmpp流 (added at 2012-10-29)
    - `body`   : 发送消息主体
    - `system` : 是否为系统消息 ( added at 2012-10-29)
    """
    frm = stanza.from_jid
    nick = get_nick(frm)
    add_history(frm, 'all', body)
    if cityid(body.strip()):
        send_command(stanza, stream, '$_tq {0}'.format(body))
        return
    tos = get_members(frm)
    if '@' in body:
        r = re.findall(r'@<(.*?)>', body)
        mem = [get_member(nick=n) for n in r if get_member(nick = n)]
        if mem:
            if body.startswith('@<'):
                b = re.sub(r'^@<.*?>', '', body)
                send_to_msg(stanza, stream, mem[0], b)
                return
            b = '%s 提到了你说: %s' % (nick, body)
            [send_to_msg(stanza, stream, to, b) for to in mem]
    elif body.strip() == 'help':
        send_command(stanza, stream, '$help')
        return
    if system: nick = 'system'
    body = "[%s] %s" % (nick, body)
    [send_msg(stanza, stream, to, body) for to in tos]


def send_to_msg(stanza, stream, to, body):
    frm = stanza.from_jid
    nick = get_nick(frm)
    add_history(frm, to, body)
    body = "[%s 悄悄对你说] %s" % (nick, body)
    send_msg(stanza, stream, to, body)
