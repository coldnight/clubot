#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/25 16:09:37
#   Desc    :   信息
#
from .db import MySQLContext as Op
from plugin.util import get_email

TABLE = "info"

def get_info(key, frm, default = None):
    email = get_email(frm)
    where = "`key`='{0}' and `email`='{1}'".format(key, email)
    with Op(TABLE) as op:
        r = op.select_one(where=where).get('value')
        if default:
            r = r if r else default
        return r

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
