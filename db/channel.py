#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   wh
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/28 13:14:07
#   Desc    :   频道db操作
#
from .db import MySQLContext as MC
from plugin.util import get_email
from settings import MODES

TABLE = 'channel'

def get_channel(name = None):
    main = {'name':'main', 'owner':'bot', 'passwd':None,
            'date':None, 'usernum':''}
    if name == 'main': return main
    with MC(TABLE) as op:
        if name:
            where = "`name`='{0}'".format(op.escape(name))
            return op.select_one(where = where)
        else:
            r = op.select()
            r = r if r else []
            r.append(main)
            return r

def add_channel(frm, name, passwd=None):
    """ 创建频道 """
    owner = get_email(frm)
    if name in MODES.keys() or name == 'main':
        return False
    with MC(TABLE) as op:
        if get_channel(name):
            return False
        fields = ('name', 'passwd', 'owner')
        values = (name, passwd, owner)
        return op.insert(fields, values)

def change_channel_pwd(frm, name, passwd):
    channel = get_channel(name = name)
    if channel.get('owner') != get_email(frm):
        return False

    with MC(TABLE) as op:
        where = "`name`='{0}'".format(op.escape(name))
        set_dict = {'passwd' : passwd}
        return op.update(set_dict, where)

def add_channel_user(name):
    if name == 'main':
        return
    with MC(TABLE) as op:
        channel = get_channel(name)
        usernum = channel.get('usernum')
        where = "`name`='{0}'".format(op.escape(name))
        set_dict = {'usernum':usernum + 1}
        return op.update(set_dict, where)

def del_channel_user(name):
    if name == 'main':
        return
    with MC(TABLE) as op:
        channel = get_channel(name)
        usernum = channel.get('usernum')
        usernum = usernum - 1 if usernum >=1 else 0
        where = "`name`='{0}'".format(op.escape(name))
        set_dict = {'usernum':usernum}
        return op.update(set_dict, where)

