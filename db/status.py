#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/25 15:28:43
#   Desc    :   状态操作
#
from pyxmpp2.jid import JID
from .db import MySQLContext
from .info import add_info
from plugin.util import get_email, NOW

def get_status(frm):
    if isinstance(frm , JID):
        where = "`email`='{0}' and `resource`='{1}'".format(get_email(frm),
                                                            frm.resource)
    else:
        where = "`email`='{0}'".format(get_email(frm))

    with MySQLContext('status') as op:
        r = op.select(where = where)
    return [v.get('statustext') for v in r]

def get_resource(frm):
    where = "email='{0}'".format(get_email(frm))
    with MySQLContext('status') as op:
        r = op.select(where = where)
    return [v.get('resource') for v in r]

def set_online(frm, statustext):
    email = get_email(frm)
    resource = frm.resource if frm.resource else ''
    with MySQLContext('status') as op:
        if get_status(frm):
            set_dict = dict(status=1)
            where = "email='{0}' and resource='{1}'".format(email, resource)
            r = op.update(set_dict, where)
        else:
            r = op.insert(('status', 'statustext', 'email', 'resource'),
                          (1, statustext, get_email(frm), resource))
    return r

def set_offline(frm):
    resource = frm.resource
    email = get_email(frm)
    where = "email='{0}' and resource='{1}'".format(email, resource)
    with MySQLContext('status') as op:
        r = op.remove(where)
    add_info('last_online', NOW(), frm)
    return r

def is_online(frm):
    email = get_email(frm)
    where = "`email`='{0}'".format(email)
    with MySQLContext('status') as op:
        r = op.select(where = where)
    stats = [v.get('status') for v in r]
    return 1 in stats

def empty_status():
    with MySQLContext('status') as op:
        return op.remove()
