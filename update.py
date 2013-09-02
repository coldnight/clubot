#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/08/28 13:30:00
#   Desc    :   从MySQL更新到MongoDB
#
import const
from db import MongoDB
from models import session, Member, Info


def mysql2mongo():
    db = MongoDB()

    members = session.query(Member)
    for m in members:
        mid = db[const.MEMBER].insert({"email":m.email, "nick":m.nick,
                                       "last_say":m.last_say,
                                       "last_change":m.last_change,
                                       "isonline":bool(m.isonline),
                                       "join_date":m.join_date})

        for info in m.infos:
            db[const.INFO].insert({"key": info.key, "value":info.value,
                                   "pubdate": info.pubdate,
                                   "is_global":bool(info.is_global),
                                   "mid":mid})

        for h in m.history:
            db[const.HISTORY].insert({"from_member":db.ref(const.MEMBER, mid),
                                      "to_member":h.to_member,
                                      "content":h.content,
                                      "pubdate":h.pubdate})

        for s in m.status:
            db[const.STATUS].insert({"status":s.status,
                                     "statustext":s.statustext,
                                     "resource":s.resource,
                                     "mid":mid})


    infos = session.query(Info).filter(Info.is_global == 1)
    for i in infos:
        db[const.INFO].insert({"key":i.key, "value":i.value,
                               "pubdate":i.pubdate,
                               "is_global":True})





if __name__ == "__main__":
    mysql2mongo()
