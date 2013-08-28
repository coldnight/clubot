#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/07/19 16:00:15
#   Desc    :   数据库操作
#
from pymongo import Connection, ASCENDING, DESCENDING
from pymongo.database import DBRef
from gridfs import GridFS
from settings import DB_HOST, DB_NAME, GFS_NAME
from bson.objectid import ObjectId

class MongoDB(object):
    desc = DESCENDING
    asc = ASCENDING
    def __init__(self):
        self.conn = None

    def ObjectId(self, _id):
        return ObjectId(_id)

    def get_objectid(self, *args):
        return ObjectId(args[0]) if len(args) == 1 else (ObjectId(a) for a in args)

    def is_objectid(self, _id):
        return isinstance(_id, ObjectId)

    def deref(self, doc):
        if isinstance(doc, DBRef):
            return self.get_db().dereference(doc)

        if isinstance(doc, list):
            r = []
            for item in doc:
                r.append(self.deref(item))
            return r

        if isinstance(doc, dict):
            r = {}
            for k, v in doc.items():
                r[k] = self.deref(v)

            return r

        return doc


    def ref(self, table, _id):
        if not isinstance(_id, ObjectId):
            _id = ObjectId(_id)

        return DBRef(table, _id)


    def get_db(self, name = None):
        if not name:
            name = DB_NAME
        host, port = DB_HOST.split(":") if ":" in DB_HOST else (DB_HOST, 27017)
        if not self.conn:
            self.conn = Connection(host = host, port = int(port), network_timeout = 60)
        return self.conn[name]

    def get_gfs(self, name = None):
        if not name:
            name = GFS_NAME
        return GridFS(self.get_db(name))

    def close(self):
        if self.conn:
            self.conn.disconnect()

    def __getitem__(self, key):
        return self.get_db()[key]

    def __getattr__(self, key):
        return self.get_db()[key]

    def __del__(self):
        self.close()
