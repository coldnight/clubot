#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/25 16:09:37
#   Desc    :   信息
#
import time
from datetime import datetime
from .db import MySQLContext as Op
from plugin.util import get_email

TABLE = "info"

def get_info(key, frm, default = None):
    email = get_email(frm)
    with Op(TABLE) as op:
        where = "`key`='{0}' and `email`='{1}'".format(op.escape(key),
                                                       op.escape(email))
        r = op.select_one(where=where).get('value')
        if default is not None:
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


def get_rp(frm):
    rp_date = get_info('rp_date', frm)
    if not rp_date: return False
    rp_date = datetime.fromtimestamp(float(rp_date))
    now = datetime.now()
    if now.year == rp_date.year and now.month == rp_date.month and \
       now.day == rp_date.day:
        return get_info('rp', frm)


def add_rp(frm, rp):
    if get_rp(frm):
        return False
    add_info('rp_date', time.time(), frm)
    add_info('rp', rp, frm)
    return True

