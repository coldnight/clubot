#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/25 15:57:08
#   Desc    :   成员操作
#
import string
from .db import MySQLContext
from .info import add_info, get_info
from .status import get_resource, is_online, get_status
from plugin.util import get_email, now
from settings import MODES, ADMINS

TABLE = "members"

def add_member(frm, name = None):
    if not name: name = frm.local
    email = get_email(frm)
    if get_member(frm): return

    fields = ('email', 'name', 'nick', 'last', 'lastchange', 'date')
    values = (email, name, name, now, now, now)
    add_info('join_time', now, frm)
    with MySQLContext(TABLE) as op:
        return op.insert(fields, values)

def del_member(frm):
    email = get_email(frm)
    where = "email='{0}'".format(email)
    with MySQLContext(TABLE) as op:
        return op.remove(where)

def edit_member(frm, nick):
    email = get_email(frm)
    with MySQLContext(TABLE) as op:
        where = "nick='{0}'".format(nick)
        if op.select(where=where): return False
        where = "email='{0}'".format(email)
        set_dict = dict(nick = nick, lastchange=now)
        add_info('last_change_nick', now, frm)
        times = get_info('change_nick_times', frm)
        times = int(times) if times else 0
        add_info('change_nick_times', times + 1, frm)
        return op.update(set_dict, where)

def get_member(frm = None, uid = None, nick = None):
    wh_list = []
    if frm:
        email = get_email(frm)
        wh_list.append('`email`="{0}"'.format(email))

    if uid:
        wh_list.append('`id`="{0}"'.format(uid))

    if nick:
        wh_list.append('`nick`="{0}"'.format(nick))

    where = ' and '.join(wh_list)
    with MySQLContext(TABLE) as op:
        return op.select_one(where = where)

def get_members(frm = None):
    where = None
    if frm:
        email = get_email(frm)
        where = "email!='{0}'".format(email)

    with MySQLContext(TABLE) as op:
        r = op.select(fields = ('email',), where = where)

    emails = [v.get('email') for v in r]
    return emails

def get_members_info():
    emails = get_members()
    result = []
    for e in emails:
        resources = get_resource(e)
        isonline = is_online(e)
        nick = get_nick(e)
        status = get_status(e)
        if isinstance(status, (str, unicode)):
            status = [status]
        status = [s for s in status if s]
        status = None if not status else ','.join(status)
        if resources:
            [result.append(dict(email = e, resource = r, status = status,
                                isonline=isonline, nick = nick))
             for r in resources]
        else:
            result.append(dict(email = e, resource = None, status = status,
                               isonline = isonline, nick = nick))
    return result

def get_nick(frm):
    email = get_email(frm)
    with MySQLContext(TABLE) as op:
        return op.select_one(where="email='{0}'".format(email)).get('nick')


user_info_template = string.Template("""昵称: $nick         状态: $status
权限: $level        当前模式: $mode
资源: $resource
更改昵称次数: $change_nick_times
上次更改昵称时间: $last_change_nick
加入时间: $join_time
最后发言: $last_say
最后在线时间: $last_online_time""")


def get_user_info(frm):
    """ 获取用户信息 """
    isonline = '在线' if is_online(frm) else '离线'
    status = get_status(frm)
    status = status[1] if len(status) == 2 else None
    status = status if status else isonline
    resource = get_resource(frm)
    join_time = get_info('join_time', frm)
    join_time = join_time if join_time else '创造之始'
    last_say = get_info('last_say', frm)
    last_say = last_say if last_say else '从未发言'
    last_change_nick = get_info('last_change_nick', frm)
    last_change_nick = last_change_nick if last_change_nick else '从未修改'
    change_nick_times = get_info('change_nick_times', frm)
    change_nick_times = change_nick_times if change_nick_times else 0
    last_online_time = get_info('last_online', frm)
    last_online_time = last_online_time if last_online_time else join_time
    level = "管理员" if get_email(frm) in ADMINS else "成员"
    mode = get_info('mode', frm)
    mode = mode if mode else 'talk'
    mode = MODES[mode]
    nick = get_nick(frm)
    result = dict(isonline = isonline, level = level, status = status,
                  join_time = join_time, mode = mode, last_say = last_say,
                  last_change_nick = last_change_nick, nick = nick,
                  resource = ','.join(resource),
                  last_online_time = last_online_time,
                  change_nick_times = change_nick_times)
    body = user_info_template.substitute(result)
    return body
