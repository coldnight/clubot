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
import time
import random
import traceback

from db.member import get_nick, get_member, edit_member, get_members
from db.member import get_members_info, del_member, get_user_info
from db.history import get_history
from db.channel import add_channel, add_channel_user, del_channel_user
from db.channel import get_channel
from db.info import add_global_info, add_info, get_info, get_rp, add_rp
from db.gtd import GTD
from settings import __version__, LOGPATH, STATUS, MODES
from util import run_code, paste_code, add_commends
from util import get_code_types, Complex, get_logger, get_email

from pyxmpp2.jid import JID

from dns import query

from dice_gtalk import roll

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
        self._cache = {}                  # 缓存
        self._modes = MODES               # 模式
        self._gtd = GTD()

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
            errorinfo = traceback.format_exc()
            body = u'{0} run command {1} happend an error:\
                    {2}'.format(get_nick(email), c, errorinfo)
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

    def _switch_channel(self, email, channel):
        """ 切换频道 """
        oldch = get_info('channel', email)
        self._logger.info('{0} switch channel from {1} to {2}'
                          .format(email, oldch, channel))
        del_channel_user(oldch)
        add_info('channel', channel, email)
        add_channel_user(channel)


class CommandHandler(BaseHandler):
    """ 普通用户命令 """
    def ls(self, stanza, *args):
        """列出成员/模式/允许的代码,发送-ls help查看用法"""
        mode = args[0] if len(args) >= 1 else None
        if mode in ['user', 'u', 'users'] or not mode:
            if len(args) > 1:
                nicks = args[1:]
                self._show_nicks(stanza, nicks)
            else:
                self._ls_channel_users(stanza)
            return
        if mode in ['a', 'all']:
                self._ls_users(stanza)
        elif mode in ['ct', 'codetype', 'code type', 'codetypes',
                      'code types']:
            self._ct(stanza)
        elif mode in ['m', 'mode', 'modes']:
            body = ''
            for m in self._modes:
                body += "{0}:{1}\n".format(m, self._modes[m])
            self._send_cmd_result(stanza, body.strip())
        elif mode in ['c', 'channel']:
            self._ls_channels(stanza)
        elif mode in ['t', 'todo']:
            self._send_cmd_result(stanza, self._gtd.show(stanza.from_jid))
        else:
            members = get_members_info()
            nicks = [m.get('nick') for m in members]
            channels = [v.get('name') for v in get_channel()]
            if mode in nicks:
                self._show_nicks(stanza, [mode])
            elif mode in channels:
                self._show_channel(stanza, mode)
            else:
                body = 'Usage: \n\
                        -ls                   查看当前频道成员\n\
                        -ls [a|all]               查看所有成员\n\
                        -ls [u|user] [nick]   查看用户\n\
                        -ls nick              查看nick的详细信息\n\
                        -ls [ct|codetype]     查看允许的代码类型\n\
                        -ls [m|mode]          列出所有模式\n\
                        -ls [CHANNEL]         查看CHANNLE频道详细信息\n\
                        -ls [c|channel]       列出所有频道\n\
                        -ls [t|todo]          列出所有代办事项'
                self._send_cmd_result(stanza, body)

    def _ls_users(self, stanza):
        """ 列出成员 """
        frm = stanza.from_jid
        femail = get_email(frm)
        members = get_members_info()
        onlinebody = []
        offlinebody = []
        els = []
        for m in members:
            email = m.get('email')
            if email in els: continue
            els.append(email)
            if email == femail:
                r = '**{0}'.format(m.get('nick'))
                onlinebody.append(r)
            elif m.get('isonline'):
                r = '*{0}'.format(m.get('nick'))
                if m.get('status'):
                    r += ' ' + m.get('status')
                onlinebody.append(r)
            else:
                r = '  ' + m.get('nick')
                offlinebody.append(r)
        onlinebody = sorted(onlinebody, key = lambda k:k.decode('utf-8')[1], reverse=False)
        offlinebody = sorted(offlinebody, key = lambda k:k.decode('utf-8')[1], reverse=False)
        body = []
        body.insert(0, 'Pythoner Club 所有成员(** 表示你自己, * 表示在线):')
        body.extend(onlinebody)
        body.extend(offlinebody)
        online_num = len(onlinebody)
        total = online_num + len(offlinebody)
        body.append('共列出 {0} 位成员 {1} 位在线'.format(total, online_num))
        self._send_cmd_result(stanza, '\n'.join(body))
        return

    def _ls_channel_users(self, stanza):
        channel = get_info('channel', stanza.from_jid)
        channel = channel if channel else 'main'
        frm = stanza.from_jid
        femail = get_email(frm)
        members = get_members_info()
        onlinebody = []
        offlinebody = []
        els = []
        for m in members:
            email = m.get('email')
            ch= get_info('channel', email)
            ch= ch if ch else 'main'
            if ch != channel: continue
            if email in els: continue
            els.append(email)
            if email == femail:
                r = '**{0}'.format(m.get('nick'))
                onlinebody.append(r)
            elif m.get('isonline'):
                r = '*{0}'.format(m.get('nick'))
                if m.get('status'):
                    r += ' ' + m.get('status')
                onlinebody.append(r)
            else:
                r = '  ' + m.get('nick')
                offlinebody.append(r)
        onlinebody = sorted(onlinebody, key = lambda k:k.decode('utf-8')[1], reverse=False)
        offlinebody = sorted(offlinebody, key = lambda k:k.decode('utf-8')[1], reverse=False)
        body = []
        body.append('当前频道({0})所有成员'.format(channel))
        body.extend(onlinebody)
        body.extend(offlinebody)
        online_num = len(onlinebody)
        total = online_num + len(offlinebody)
        body.append('共列出 {0} 位成员 {1} 位在线'.format(total, online_num))
        self._send_cmd_result(stanza, '\n'.join(body))
        return

    def _ls_channels(self, stanza):
        channels = get_channel()
        body = [u'当前所有频道']
        for c in channels:
            name = c.get('name')
            passwd = c.get('passwd')
            if passwd:
                name += ' *'
            body.append(name)
        self._send_cmd_result(stanza, '\n'.join(body))

    def _show_nicks(self, stanza, nicks):
        """ 显示所有昵称的信息 """
        emails = [get_member(nick = n) for n in nicks]
        infos = [self._whois(e.get('email')) for e in emails]
        body = '\n\n'.join(infos)
        self._send_cmd_result(stanza, body)

    def _whois(self, frm):
        body = get_user_info(frm)
        return body

    def _show_channel(self, stanza, name):
        channel = get_channel(name)
        name = channel.get('name')
        usernum = channel.get('usernum')
        passwd = channel.get('passwd')
        isencrypt = u'是' if passwd else u'否'
        owner = channel.get('owner')
        nick = get_nick(owner) if owner != 'bot' else owner
        body = "频道名称: {0}           频道人数: {1}\n"\
                "是否加密: {2}           拥有者:{3}".format(name, usernum,
                                                            isencrypt, nick)
        if owner == stanza.from_jid.bare().as_string() and passwd:
            body +="\n频道密码: "+ passwd
        self._send_cmd_result(stanza, body)

    def cd(self, stanza, *args):
        """ 进入模式/频道 """
        mode = args[0] if len(args) >= 1 else None
        channels = get_channel()
        cnames = [v.get('name') for v in channels]
        if not mode or (mode not in self._modes and mode not in cnames):
            body = "Usage:\n\
                    -cd MODE/CHANNEL    进入MODE模式,使用-ls m查看允许的模式"
        else:
            if mode in self._modes:
                add_info('mode', mode, stanza.from_jid)
                body = " 你已进入{0}".format(self._modes[mode])
            else:
                current_channel = [v for v in channels
                                   if v.get('name') == mode][0]
                uc = get_info('channel', stanza.from_jid)
                uc = uc if uc else 'main'
                if uc == current_channel.get('name'):
                    body = u'你已经在 {0}  频道'.format(mode)
                    return self._send_cmd_result(stanza, body)
                else:
                    del_channel_user(uc)
                if current_channel.get('passwd'):
                    pwd = args[1] if len(args) == 2 else None
                    if pwd == current_channel.get('passwd'):
                        add_info('channel', mode, stanza.from_jid)
                        add_channel_user(mode)
                        body = " 你已进入 {0} 频道".format(mode)
                    else:
                        body = " 频道密码错误"
                        if not pwd:
                            body = u"频道已加密,需要密码"
                else:
                    add_info('channel', mode, stanza.from_jid)
                    add_channel_user(mode)
                    body = " 你已进入 {0} 频道".format(mode)

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
        self._message_bus.send_all_msg(stanza, body)

    def r(self,stanza,*args):
        """20面骰子,使用:1d20+1 攻击 @submit by:欧剃 @add by: eleven.i386"""
        nick = get_nick(stanza.from_jid)
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
        rp = get_rp(frm)
        nick = get_nick(frm)
        if not rp:
            t = random.randrange(1, 10)
            rps = [random.randrange(0, 100) for i in xrange(0, t)]
            rp = rps[random.randrange(0, len(rps) -1)] if len(rps) > 1 else rps[0]
            add_rp(frm, rp)
            body = ">>>{0} 进行了今日人品检测,人品值为 {1}".format(nick, rp)
            self._message_bus.send_sys_msg(stanza, body)
        else:
            body = "你已经检测过了今天的人品,人品值为 {0}".format(rp)
            self._send_cmd_result(stanza, body)

    def _ping(self, stanza, *args):
        self._send_cmd_result(stanza, 'is ok, I am online')


    def mt(self, stanza, *args):
        """单独给某用户发消息"""
        if len(args) <= 1: return self.help(stanza, 'msgto')
        nick = args[0]
        receiver = get_member(nick = nick).get('email')
        if receiver == stanza.from_jid.bare().as_string():
            self._send_cmd_result(stanza, "请不要自言自语")
            return
        body = ' '.join(args[1:])
        if not receiver:
            self._send_cmd_result(stanza, "%s 用户不存在" % nick)
        else:
            self._message_bus.send_private_msg(stanza, receiver, body)


    def nick(self, stanza, *args):
        """更改昵称 eg. -nick yournewnickname"""
        if len(args) < 1: return self.help(stanza, 'nick')
        nick = ' '.join(args[0:])
        channels = [v.get('name') for v in get_channel()]
        if nick in self._invaild or nick in channels:
            return self._send_cmd_result(stanza, '昵称不合法')
        frm = stanza.from_jid
        oldnick = get_nick(frm)
        r = edit_member(frm, nick = nick)
        if r:
            body = "%s 更改昵称为 %s" % (oldnick, nick)
            self._message_bus.send_sys_msg(stanza, body)
            self._send_cmd_result(stanza, u'你的昵称现在的已经已经更改为 {0}'.format(nick))
        else:
            self._send_cmd_result(stanza, '昵称已存在')


    def code(self, stanza, *args):
        """<type> <code> 贴代码,使用-ls ct 查看允许的代码类型"""
        if len(args) <= 1: return self.help(stanza, 'code')
        nick = get_nick(stanza.from_jid)
        typ = args[0]
        #codes = add_commends(args[1:], typ, nick)
        codes = args[1:]
        codes = ''.join(codes[0:2]) + ' '.join(codes[2:])
        poster = "Pythoner Club: %s" % nick
        r = paste_code(poster,typ, codes)
        if r:
            self._message_bus.send_all_msg(stanza, r)
            self._send_cmd_result(stanza, r)
        else:
            self._send_cmd_result(stanza, '代码服务异常,通知管理员')

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

    def py(self, stanza, *args):
        """ 执行Python代码 """
        if len(args) < 1: return self.help(stanza, 'py')
        code = ' '.join(args)
        result = run_code(code)
        body = u'>>> {0}\n'.format(code)
        body += result
        self._message_bus.send_all_msg(stanza, body)
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
        self._message_bus.send_subscribe(JID(to))


    def history(self, stanza, *args):
        """显示聊天历史"""
        sef = stanza.from_jid
        if args:
            self._send_cmd_result(stanza, get_history(sef, *args))
        else:
            self._send_cmd_result(stanza, get_history(sef))

    def me(self, stanza, *args):
        """ 查看自己的详细信息 """
        body = self._whois(stanza.from_jid)
        self._send_cmd_result(stanza, body)

    def todo(self, stanza, *args):
        """ 添加TODO事项 """
        task = " ".join(args)
        frm = stanza.from_jid
        if task.strip():
            self._gtd.todo(task, stanza.from_jid)
        self._send_cmd_result(stanza, self._gtd.show(frm))

    def gtd(self, stanza, *args):
        """ 时间管理, 管理TODO事项 """
        tid = None if len(args) < 2 else args[1]
        frm = stanza.from_jid
        help_info = "-gtd show   列出所有todo事项\n"\
                    "-gtd up TASKID 提升TASKID的todo事项的优先级\n"\
                    "-gtd down TASKID 降低TASKID的todo事项的优先级\n"\
                    "-gtd expirse TASKID TIME 设置TASKID的todo事项的过期时间\n\
                                 TIME可以为 1m/1h/1d or YYYY-MM-DD HH:MM\n"\
                    "-gtd done TASKID    完成id为TASKID的TODO事项\n"\
                    "-gtd postpone TASKID 推迟id为TASKID的TODO事项\n"\
                    "-gtd drop TASKID    删除id为TASKID的TODO事项"
        if len(args) < 1:
            return self._send_cmd_result(stanza, help_info)
        arg = args[0]
        if arg == "show":
            body = self._gtd.show(frm)
        elif arg == "up" and tid:
            body = self._gtd.up(args[1], frm)
        elif arg == "down" and tid:
            body = self._gtd.down(args[1], frm)
        elif arg == "expirse" and tid and len(args) >= 3:
            body = self._gtd.expirse(args[1], " ".join(args[2:]), frm)
        elif arg == "done" and tid:
            body = self._gtd.done(args[1], frm)
        elif arg == "postpone" and tid:
            body = self._gtd.postpone(args[1], frm)
        elif arg == "drop" and tid:
            body = self._gtd.drop(args[1], frm)
        elif arg == "help":
            body = help_info
        else:
            body = help_info

        if body:
            self._send_cmd_result(stanza, body)

    def version(self, stanza, *args):
        """显示版本信息"""
        author = ['cold(wh_linux@126.com)',
                    'eleven.i386(eleven.i386@gmail.com)',]
        body = "version %s\nauthors\n\t%s\n" % (__version__,
                                                '\n\t'.join(author))
        body += "\nhttps://github.com/coldnight/clubot"
        return self._send_cmd_result(stanza, body)


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
        emails = [get_member(nick = n) for n in args]
        if len(emails) < 1: return self.help(stanza, 'rm')
        for e in emails:
            jid = JID(e)
            del_member(jid)
            self._message_bus.send_unsubscribe(jid)

    def cs(self, stanza, *args):
        """ 更改状态 """
        if args:
            status = ' '.join(args)
        else:
            status = STATUS
        add_global_info('status', status)
        self._message_bus.send_status(status)

    def cc(self, stanza, *args):
        """ 创建频道 """
        name = args[0] if len(args) >= 1 else None
        if not name:
            return self._send_cmd_result(u'使用 -cc CHANNEL [PASSWORD] 创建CHANNEL')
        passwd = args[1] if len(args) >=2 else None
        r = add_channel(stanza.from_jid, name, passwd)
        if r:
            body = u'{0} 频道创建成功'.format(name)
        else:
            body = u'频道已存在或名称不合法'.format(name)
        self._send_cmd_result(stanza, body)

    def mv(self, stanza, *args):
        """ 移动用户到指定频道 """
        if len(args) < 2:
            body = u'Usage: -mv NICK CHANNLE'
            return self._send_cmd_result(stanza, body)
        if args[1] == '.':
            distch = get_info('channel', stanza.from_jid)
        else:
            distch = args[1]
        if args[0] == '*':
            members = get_members(stanza.from_jid)
            emails = [v for v in members if get_info('channel', v) != distch]
        else:
            info = get_member(nick = args[0])
            emails = [info.get('email')]
        channel = get_channel(distch)
        if not emails:
            body = u'{0} 成员不存在'.format(args[0])
            return self._send_cmd_result(stanza, body)

        if not channel:
            body = u'{0} 频道不存在'.format(args[1])
            return self._send_cmd_result(stanza, body)
        nick = get_nick(stanza.from_jid)
        body = '{0} 将你移动到 {1} 频道'.format(nick, distch)
        nicks = []
        for email in emails:
            nicks.append(get_nick(email))
            self._switch_channel(email, distch)
            self._message_bus.send_message(stanza, email, body)
        body = '你将 {0} 移动到 {1} 频道'.format(','.join(nicks), distch)
        self._send_cmd_result(stanza, body)
