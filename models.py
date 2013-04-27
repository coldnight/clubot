#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/25 10:56:18
#   Desc    :   模型
#
from sqlalchemy import (Column, Integer, String, TEXT, TIMESTAMP, ForeignKey,
                        create_engine )
from sqlalchemy.orm import sessionmaker, relation
from sqlalchemy.ext.declarative import declarative_base

from utility import get_email, now
from settings import DB_HOST, DB_PORT, DB_USER, DB_PASSWD, DB_NAME, DEBUG

db_scheme = "mysql://{0}:{1}@{2}:{3}/{4}?charset=utf8".format(DB_USER,DB_PASSWD,
                                                 DB_HOST, DB_PORT,
                                                 DB_NAME)
DEBUG = False
engine = create_engine(db_scheme, echo = DEBUG)

Session = sessionmaker(bind = engine)
session = Session()

Base = declarative_base()

class Member(Base):
    __tablename__ = "clubot_members"

    id = Column(Integer, primary_key = True)
    email = Column(String(100), unique = True)
    nick = Column(String(50), unique = True)
    last_say = Column(TIMESTAMP, nullable = True)
    last_change = Column(TIMESTAMP)
    isonline = Column(Integer, default = 1)
    join_date = Column(TIMESTAMP)

    def __init__(self, jid, nick = None):
        self.nick = nick if nick else jid.local
        self.email = get_email(jid)
        self.join_date = now()

    def __repr__(self):
        return u"<Member ('%s', '%s')>" % (self.nick, self.email)


class Info(Base):
    __tablename__ = "clubot_infos"

    id = Column(Integer, primary_key = True)
    key = Column(String(255))
    value = Column(TEXT)
    pubdate = Column(TIMESTAMP)
    is_global = Column(Integer, default=0)

    member_id = Column(Integer, ForeignKey("clubot_members.id"))
    member = relation("Member", backref="infos", lazy=False)

    def __init__(self, key, value, is_global = False):
        self.key = key
        self.value = value
        self.is_global = 1 if is_global else 0
        self.pubdate = now()

    def __repr__(self):
        return u"<Info ('%s', '%s')>" % (self.key, self.value)


class History(Base):
    __tablename__ = "clubot_history"

    id = Column(Integer, primary_key = True)

    from_member = Column(Integer, ForeignKey("clubot_members.id"))
    to_member = Column(String(100))

    member = relation("Member", backref="history", lazy=False)

    content = Column(TEXT)
    pubdate = Column(TIMESTAMP)

    def __init__(self, to_member, content):
        self.to_member = get_email(to_member)
        self.content = content
        self.pubdate = now()

    def __repr__(self):
        return u"<History '%s'>" % self.content


class Status(Base):
    __tablename__ = "clubot_status"

    id = Column(Integer, primary_key = True)

    status = Column(Integer, default=1)
    statustext = Column(String(100), nullable=True)
    resource = Column(String(255), nullable = True)

    member_id = Column(Integer, ForeignKey("clubot_members.id"))

    member = relation("Member", backref="status", lazy=False)


    def __init__(self, statustext = None, resource = None, status = 1):
        self.statuxtext = statustext
        self.resource = resource
        self.status = status

    def __repr__(self):
        return "<Status %d %r>" % (self.status, self.statustext)

Base.metadata.create_all(engine)
