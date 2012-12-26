#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/25 15:57:08
#   Desc    :   成员操作
#
from .db import MySQLContext
from .info import add_info, get_info
from .status import get_resource, is_online, get_status
from plugin.util import get_email, now

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
            result.update(dict(email = e, resource = None, status = status,
                               isonline = isonline, nick = nick))
    return result

def get_nick(frm):
    email = get_email(frm)
    with MySQLContext(TABLE) as op:
        return op.select_one(where="email='{0}'".format(email)).get('nick')
