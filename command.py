#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# 生成命令
#
# Author : cold
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
import json
import time
import gzip
import random
import traceback
from cStringIO import StringIO
from datetime import datetime
from functools import partial

from dns import query

from pyxmpp2.jid import JID
from tornadohttpclient import TornadoHTTPClient

from logics import Logics
from settings import  LOGPATH, STATUS, MODES, ADMINS, USER
from utility import  get_logger, get_email, roll, cityid, nicetime

from settings import YOUDAO_KEY, YOUDAO_KEYFROM
from honor import Honor


class BaseHandler(object):
    """ 命令处理基类
        命令对应着方法
        比如敲入 -ls 则对应ls方法
        需要参数自行从args里提取
    """
    _invaild = ['u', 'm', 'c', 'mode', 'user', 'main', 'channel',
                'ct', 'codetype', 'users', 'a', 'all', '>>>']
    def __init__(self, message_bus):
        self._message_bus = message_bus   # 消息总线
        self._logger = get_logger()       # 日志
        self._http_stream = TornadoHTTPClient()
        self._honor = Honor()

    def _send_cmd_result(self, stanza, body):
        """返回命令结果"""
        self._message_bus.send_back_msg(stanza, body)

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
        """ 解析命令和参数 """
        cmd = cmd.strip()
        splitbody = cmd.split('\n')
        if len(splitbody) >= 2:
            cmdline = (splitbody[0], '\n'.join(splitbody[1:]))
        else:
            cmdline= splitbody
        tmp = list(cmdline)
        cmdline = tmp[0].split(' ') + tmp[1:]
        return cmdline[0], cmdline[1:]

    def _run_cmd(self, stanza, body):
        """ 执行命令 """
        cmd = body[1:]
        c, args = self._parse_args(cmd)
        email = get_email(stanza.from_jid)
        cmds = [v.get('name') for v in self._get_cmd()]
        cmds.append('_ping')
        cmds.append('_tq')
        if c not in cmds:
            self._message_bus.send_all_msg(stanza, body)
            return
        try:
            self._logger.info('%s run cmd %s', email, c)
            m =getattr(self, c)(stanza, *args)
        except Exception as e:
            self._logger.warning(e.message)
            nick = Logics.get_one(stanza.from_jid).nick
            errorinfo = traceback.format_exc()
            body = u'{0} run command {1} happend an error:\
                    {2}'.format(nick, c, errorinfo)
            self._message_bus.send_to_admin(stanza, body)
            self._message_bus.send_back_msg(stanza, c + ' 命令异常,已通知管理员')
            return

        return m

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


class CommandHandler(BaseHandler):
    """ 普通用户命令 """
    def ls(self, stanza, *args):
        """列出成员"""
        frm = stanza.from_jid
        femail = get_email(frm)
        members = Logics.get_members(status = True)
        onlines = []
        offlines = []
        for m in members:
            if m.email == USER:
                continue
            status = m.status
            isonline = bool([status.status for status in m.status
                         if status.status])
            status_text = ""
            status = [status.statustext for status in m.status if status.statustext]
            if "away" in status:
                status_text = "「离开」"

            if "dnd" in status:
                status_text = "「忙碌」"

            if m.email == femail:
                onlines.append("** {0}".format(m.nick))
            elif m.email != femail and isonline:
                onlines.append("* {0} {1}".format(m.nick, status_text))
            else:
                offlines.append("  {0}".format(m.nick))
        onlines = sorted(onlines, key = lambda k:k.decode('utf-8')[1],
                         reverse=True)
        offlines = sorted(offlines, key = lambda k:k.decode('utf-8')[1],
                          reverse=True)
        body = []
        body.insert(0, 'Pythoner Club 所有成员(** 表示你自己, * 表示在线):')
        body.extend(onlines)
        body.extend(offlines)
        online_num = len(onlines)
        total = online_num + len(offlines)
        body.append('共列出 {0} 位成员 {1} 位在线'.format(total, online_num))
        self._send_cmd_result(stanza, '\n'.join(body))


    def cd(self, stanza, *args):
        """ 切换模式: cd talk 进入聊天模式, cd quiet 进入安静模式(不接收消息)"""
        mode = " ".join(args)
        if not mode:
            self._send_cmd_result(stanza, u"进入哪里? talk or quiet?")
            return

        if mode in MODES.keys():
            Logics.set_info(stanza.from_jid, "mode", mode)
            body = u"你已进入 {0}".format(MODES[mode])
            self._send_cmd_result(stanza, body)
        else:
            self._send_cmd_result(stanza, u"我不知道 {0} 这种模式".format(mode))


    def _tq(self, stanza, *args):
        """指定城市获取天气"""
        body = ''.join([x for x in args])
        key = cityid(body.encode('utf-8'))
        url = 'http://www.weather.com.cn/data/cityinfo/' + key + ".html"
        def readback(resp):
            load = json.loads(resp.read())
            body = 'city:%s, Weather %s, %s ~ %s' %\
                    (load['weatherinfo']['city'],
                     load['weatherinfo']['weather'],
                     load['weatherinfo']['temp1'],
                     load['weatherinfo']['temp2'])
            self._send_cmd_result(stanza, body)
            self._message_bus.send_all_msg(stanza, body)

        self._http_stream.get(url, callback = readback)


    def r(self,stanza,*args):
        """20面骰子,使用:1d20+1 攻击 @submit by:欧剃 @add by: eleven.i386"""
        nick = Logics.get_one(stanza.from_jid).nick
        try:
            result = roll(' '.join(args))
            body = ">>> {0} {1}".format(nick, result)
            self._message_bus.send_sys_msg(stanza, body)
        except:
            body = u'请发送: -roll 1d20+n A (n是数字 A是动作比如攻击)'
            self._send_cmd_result(stanza, body)

    def rp(self, stanza, *args):
        """ 测试今日RP """
        frm = stanza.from_jid
        nick = Logics.get_one(frm).nick
        rp = Logics.get_today_rp(frm)
        if rp == None:
            t = random.randrange(1, 10)
            rps = [random.randrange(0, 100) for i in xrange(0, t)]
            rp = rps[random.randrange(0, len(rps) -1)] if len(rps) > 1 else rps[0]
            Logics.set_today_rp(frm, rp)
            body = ">>>{0} 进行了今日人品检测,人品值为 {1}".format(nick, rp)
            self._message_bus.send_sys_msg(stanza, body)
            self._honor.rp_honor(nick, rp, partial(self._message_bus.send_sys_msg, stanza))
        else:
            body = "你已经检测过了今天的人品,人品值为 {0}".format(rp)
            self._send_cmd_result(stanza, body)

    def _ping(self, stanza, *args):
        self._send_cmd_result(stanza, 'is ok, I am online')


    def mt(self, stanza, *args):
        """单独给某用户发消息"""
        if len(args) <= 1: return self.help(stanza, 'msgto')
        nick = args[0]
        receiver = Logics.get_with_nick(nick = nick).email
        if receiver == stanza.from_jid.bare().as_string():
            self._send_cmd_result(stanza, "请不要自言自语")
            return
        body = ' '.join(args[1:])
        if not receiver:
            self._send_cmd_result(stanza, "%s 用户不存在" % nick)
        else:
            self._message_bus.send_private_msg(stanza, receiver, body)


    def whois(self, stanza, *args):
        """ 查询用户信息 """
        nick = ' '.join(args[0:])
        m = Logics.get_with_nick(nick, status = True, infos = True,
                                 history = True)
        if not m:
            self._send_cmd_result(stanza, u"{0} 用户不存在".format(nick))
            return
        bodys = []
        sts = [status.statustext for status in m.status if status.statustext]
        status_text = u""
        if "away" in sts:
            status_text = u"「离开」"

        if "dnd" in sts:
            status_text = u"「忙碌」"

        isonline = bool([status.status for status in m.status
                        if status.status])
        status = u"在线"+status_text if isonline else u"离线"
        resource = " ".join(s.resource for s in m.status if s.resource)
        rp = Logics.get_today_rp(m.email)
        rp = rp if rp != None else u"尚未测试"
        say_times = 0 if not m.history else len(m.history)
        level = u"管理员" if m.email in ADMINS else u"成员"
        last_say = u"从未发言" if not m.last_say else m.last_say
        last_change = m.last_change if m.last_change else u"从未修改"
        change_times = Logics.get_info(m.email, "change_nick_times", 0).value
        mode = Logics.get_info(stanza.from_jid, 'mode').value
        is_rece = u"是" if mode != "quiet" else u"否"
        bodys.append(u"昵称: {0}     状态: {1}".format(m.nick, status))
        bodys.append(u"资源: {0}     权限: {1}".format(resource, level))
        bodys.append(u"今日人品: {0}".format(rp))
        bodys.append(u"发言次数: {0}".format(say_times))
        bodys.append(u"最后发言: {0}".format(nicetime(last_say)))
        bodys.append(u"加入时间: {0}".format(nicetime(m.join_date)))
        bodys.append(u"更改昵称次数: {0}".format(change_times))
        bodys.append(u"上次更改时间: {0}".format(nicetime(last_change)))
        bodys.append(u"是否接受消息: {0}".format(is_rece))
        honor = Logics.get_honor_str(m)
        if honor:
            bodys.append(u"成就:")
            bodys.append(honor)
        self._send_cmd_result(stanza, "\n".join(bodys))


    def nick(self, stanza, *args):
        """更改昵称 eg. -nick yournewnickname"""
        if len(args) < 1: return self.help(stanza, 'nick')
        nick = ' '.join(args[0:])
        frm = stanza.from_jid
        oldnick = Logics.get_one(frm).nick
        if nick == oldnick:
            self._send_cmd_result(stanza, u"你已经在使用这个昵称")
            return
        r = Logics.modify_nick(frm, nick)
        if r:
            body = "%s 更改昵称为 %s" % (oldnick, nick)
            self._message_bus.send_sys_msg(stanza, body)
            self._send_cmd_result(stanza, u'你的昵称现在的已经已经更改为 {0}'.format(nick))
        else:
            self._send_cmd_result(stanza, u'昵称已存在')


    def shell(self, stanza, *args):
        """ 一个Python shell, 也可通过 >>> <statement>来执行"""
        if len(args) < 1: return self.help(stanza, 'shell')
        code = ' '.join(args)
        email = get_email(stanza.from_jid)
        if code.strip() in ["cls", "clear"]:
            url = "http://pythonec.appspot.com/drop"
            params = [("session", email),]
        else:
            url = "http://pythonec.appspot.com/shell"
            #url = "http://localhost:8880/shell"
            params =  dict(session = email, statement=code.encode("utf-8"))


        def read_shell(resp):
            result = resp.read()
            nick = Logics.get_one(stanza.from_jid).nick
            if not result:
                nick = "{0}:[OK]".format(nick)
            else:
                nick = "{0}:[OUT]".format(nick)

            if len(result) > 200:
                callback = partial(self._message_bus.send_sys_msg, stanza)
                self._paste(stanza, "python", result, nick, callback)
            else:
                self._message_bus.send_sys_msg(stanza, u"{0} {1}"
                                               .format(nick, result))

        self._http_stream.get(url, params, callback = read_shell)


    def _paste(self, stanza, typ, code, nick, callback):
        """ 贴代码, paste <type> <code>
        参数
            stanza  消息节
            typ     类型
            code    代码
            nick    昵称
            callback    回调
        """
        param = {'vimcn':code.encode("utf-8")}
        url = "http://p.vim-cn.com/"
        def __paste(resp):
            nurl = resp.body.strip().rstrip("/") + "/" + typ
            callback("{0} {1}".format(nick, nurl))

        self._http_stream.post(url, param, callback = __paste)


    def dns(self, stanza, *args):
        """ 使用VPS解析主机名 """
        if len(args) < 1: return self.help(stanza, 'dns')
        host = ' '.join(args)
        host = host.split(' ')[0]
        try:
            result = query.socket.gethostbyname_ex(host.strip())[-1]
            result = list(set(result))
            result = '\n'.join(result)
        except:
            result = "解析失败"
        self._send_cmd_result(stanza, result)


    def it(self, stanza, *args):
        """邀请好友加入 eg. -it <yourfirendemail>"""
        if len(args) < 1:return self.help(stanza, 'invite')
        to = args[0]
        self._message_bus.send_subscribe(JID(to))


    def old(self, stanza, *args):
        """显示聊天历史, 后面可跟昵称查看某人的历史, 或跟时间查看多长时间以内的历史:1h, 2h, 1d"""
        last = " ".join(args)
        m = Logics.get_with_nick(last)
        unit_map = {"h":3600, "m":60, "d":86400}
        header_map = {"h":u"小时", "m":u"分钟", "d":u"天"}
        two_hours_ago = datetime.fromtimestamp(time.time() - 7200)
        header = u"两小时以内的历史消息:"
        kwargs = {"starttime":two_hours_ago}
        if last:
            if m:
                kwargs["jid"] = m.email
                header = u"{0} 发送的历史消息:".format(m.nick)
            else:
                if last[0:-1].isdigit():
                    num, unit = int(last[0:-1]), last[-1].lower()
                    starttime = time.time() - (num * unit_map.get(unit, 3600))
                    starttime = datetime.fromtimestamp(starttime)
                    kwargs["starttime"] = starttime
                    header = u"{0} {1} 之内的历史消息:"\
                            .format(num, header_map.get(unit, u"小时"))

        histories = Logics.get_history(**kwargs)
        bodys = [header]
        for history in histories:
            bodys.append(u"{0} [{1}] {2}".format(nicetime(history.get("pubdate")),
                                                 history.get("from_member", {}).get("nick"),
                                                 history.get("content")))

        self._send_cmd_result(stanza, "\n".join(bodys))


    def me(self, stanza, *args):
        """ 查看自己的详细信息 """
        self.whois(stanza, Logics.get_one(stanza.from_jid).nick)

    def tr(self, stanza, *args):
        """ 调用有道接口进行英汉互译 """
        key = YOUDAO_KEY
        keyfrom = YOUDAO_KEYFROM
        source = " ".join(args)
        source = source.encode("utf-8")
        url = "http://fanyi.youdao.com/openapi.do"
        params = [("keyfrom", keyfrom), ("key", key),("type", "data"),
                  ("doctype", "json"), ("version",1.1), ("q", source)]

        def read_back(resp):
            source = resp.read()
            body = None
            try:
                buf = StringIO(source)
                with gzip.GzipFile(mode = "rb", fileobj = buf) as gf:
                    data = gf.read()
            except:
                self._logger.warn(traceback.format_exc())
                data = source

            try:
                result = json.loads(data)
            except ValueError:
                self._logger.warn(traceback.format_exc())
                body = u"error"
            else:
                errorCode = result.get("errorCode")
                if errorCode == 0:
                    query = result.get("query")
                    r = " ".join(result.get("translation"))
                    basic = result.get("basic", {})
                    body = u"{0}\n{1}".format(query, r)
                    phonetic = basic.get("phonetic")
                    if phonetic:
                        ps = phonetic.split(",")
                        if len(ps) == 2:
                            pstr = u"读音: 英 [{0}] 美 [{1}]".format(*ps)
                        else:
                            pstr = u"读音: {0}".format(*ps)
                        body += u"\n" + pstr

                    exp = basic.get("explains")
                    if exp:
                        body += u"\n其他释义:\n\t{0}".format(u"\n\t".join(exp))

                        """
                        if web:
                            for w in web:
                                body += u"\t{0}\n".format(w.get("key"))
                                vs = u"\n\t\t".join(w.get("value"))
                                body += u"\t\t{0}\n".format(vs)
                        """

                if errorCode == 50:
                    body = u"无效的有道key"

            if not body:
                body = u"没有结果"
            self._send_cmd_result(stanza, body)

        self._http_stream.get(url, params, callback =read_back)


class AdminCMDHandler(CommandHandler):
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
        emails = [Logics.get_with_nick(n).email for n in args]
        if len(emails) < 1: return self.help(stanza, 'rm')
        for e in emails:
            jid = JID(e)
            Logics.drop(jid)
            self._message_bus.send_unsubscribe(jid)

    def cs(self, stanza, *args):
        """ 更改状态 """
        if args:
            status = ' '.join(args)
        else:
            status = STATUS
        Logics.set_global_info("status", status)
        self._message_bus.send_status(status)
