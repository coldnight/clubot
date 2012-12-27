#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/25 16:09:37
#   Desc    :   信息
#
import string
from .db import MySQLContext as Op
from .status import get_status, is_online, get_resource
from plugin.util import get_email
from settings import MODES, ADMINS

TABLE = "info"

def get_info(key, frm):
    email = get_email(frm)
    where = "`key`='{0}' and `email`='{1}'".format(key, email)
    with Op(TABLE) as op:
        return op.select_one(where=where).get('value')

def add_info(key, value, frm):
    email = get_email(frm)
    where = "`key`='{0}' and `email`='{1}'".format(key, email)
    with Op(TABLE) as op:
        if get_info(key, frm) is not None:
            set_dic = dict(value=value)
            return op.update(set_dic, where)
        else:
            fields = ('email', 'key', 'value')
            values = (email, key, value)
            return op.insert(fields, values)

def get_global_info(key):
    return get_info(key, 'global')

def add_global_info(key, value):
    return add_info(key, value, 'global')

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
    result = dict(isonline = isonline, level = level, status = status,
                  join_time = join_time, mode = mode, last_say = last_say,
                  last_change_nick = last_change_nick,
                  resource = ','.join(resource),
                  last_online_time = last_online_time,
                  change_nick_times = change_nick_times)
    return result


user_info_template = string.Template("""昵称: $nick         状态: $status
权限: $level        当前模式: $mode
资源: $resource
更改昵称次数: $change_nick_times
上次更改昵称时间: $last_change_nick
加入时间: $join_time
最后发言: $last_say
最后在线时间: $last_online_time""")
