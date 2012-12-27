#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   wh
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/25 16:38:07
#   Desc    :   聊天历史
#
from .db import MySQLContext
from .member import get_nick
from plugin.util import NOW, get_email

def add_history(frm, to, content):
    email = get_email(frm)
    fields = ('frmemail', 'toemail', 'content', 'date')
    values = (email, to, content, NOW())
    with MySQLContext('history') as op:
        return op.insert(fields, values)


def get_history(sef, index = 1,  size = 10):
    where = "`toemail`='{0}' or `toemail`='all'"
    limit = int(size)
    skip = (int(index) -1) * limit
    with MySQLContext('history') as op:
        result = op.select(where = where, limit = (skip, limit),
                           order = dict(id = -1))
    body = '第{0}页历史\n'.format(index)
    for r in result:
        date = r.get('date')
        nick = get_nick(r.get('frmemail'))
        content = r.get('content')
        if r.get('toemail') == sef:
            nick = nick + ' 悄悄对你说'
        body += '{0} [{1}] {2}\n'.format(date, nick, content)

    return body.strip()

