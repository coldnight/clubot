#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
# 设置
"""
import os
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

ADMINS = ['coldnight.linux@gmail.com']

USER = 'pythonerclub@gmail.com'

PASSWORD = ''

DEBUG = False

IMPORT = False # 如果数据库中有而角色中无则添加好友

__version__ = '0.2.0 alpha-threading'

PIDPATH = r'logs/clubot.pid'

LOGPATH = r'logs/clubot.log'

DB_PATH= os.path.join(os.path.dirname(__file__), 'plugin/group.db')

DB_HOST = 'localhost'

DB_PORT = 3306

DB_NAME = 'clubot'

DB_USER = 'root'

DB_PASSWD = ''

STATUS = u"Pythoner Club Linux/Vim/Python 技术交流"

# DEBUG:10
# INFO : 20
# WARNING :30
# ERROR : 40
# CRITICAL: 50
LOGLEVEL = 10
