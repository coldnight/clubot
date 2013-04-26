#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/25 18:10:23
#   Desc    :   更新脚本,用于导入老数据
#
import models

from sqlalchemy import Column, Integer, String, TEXT, TIMESTAMP


class OldMember(models.Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key = True)
    email = Column(String(100))
    name = Column(String(100))
    nick = Column(String(50))
    last = Column(TIMESTAMP)
    lastchange = Column(TIMESTAMP)
    isonline = Column(Integer, default=1)
    date = Column(TIMESTAMP)


class OldInfo(models.Base):
    __tablename__ = "info"

    id = Column(Integer, primary_key = True)
    email = Column(String(100))
    key = Column(String(255))

    value = Column(TEXT)
    createdate = Column(TIMESTAMP)


class OldHistory(models.Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key = True)
    frmemail = Column(String(100))
    toemail = Column(String(100))
    content = Column(TEXT)
    date = Column(TIMESTAMP)

def update():
    oldms = models.session.query(OldMember).all()
    for om in oldms:
        m = models.Member(om.email, om.nick.decode("utf-8"))
        m.last_say = om.last
        m.last_change = om.lastchange
        m.join_date = om.date
        histories = models.session.query(OldHistory)\
                .filter(OldHistory.frmemail == om.email).all()
        for history in histories:
            h = models.History(history.toemail, history.content.decode("utf-8"))
            h.pubdate = history.date
            if m.history:
                m.history.append(h)
            else:
                m.history = [h]

        oldinfos = models.session.query(OldInfo)\
                .filter(OldInfo.email == om.email).all()
        for oi in oldinfos:
            nin = models.Info(oi.key, oi.value.decode("utf-8"))
            if m.infos:
                m.infos.append(nin)
            else:
                m.infos = [nin]
        models.session.add(m)

    oginfos = models.session.query(OldInfo).filter(OldInfo.email == "global").all()
    for oi in oginfos:
        nin = models.Info(oi.key, oi.value.decode("utf-8"), True)
        models.session.add(nin)

    models.session.commit()

if __name__ == "__main__":
    update()
