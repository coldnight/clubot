#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/21 15:58:35
#   Desc    :   工具类函数
#
import re
import logging
import traceback
import urllib, urllib2, json
from datetime import datetime
from settings import DEBUG
from settings import LOGPATH
from settings import USER
from city import cityid


NOW = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
now = datetime.now()

def http_helper(url, param = None, callback=None):
    if param:
        data = urllib.urlencode(param)
        req =urllib2.Request(url,data)
    else:
        req = urllib2.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:14.0) Gecko/20100101 Firefox/14.0.1")
    res = urllib2.urlopen(req)

    if callback:
        result = callback(res)
    else:
        result =  res.read()
    return result

def http_helper2(url, params, method = 'POST'):
    """ http请求辅助函数 """
    params = urllib.urlencode(params)
    if method.lower() == 'post':
        request = urllib2.Request(url, params)
    elif method.lower() == 'get':
        url += '?'+params
        request = urllib2.Request(url)
    else:
        raise ValueError('method error')

    response = urllib2.urlopen(request)
    tmp = response.read()
    result = json.loads(tmp)
    return result

def run_code(code):
    CODERUN = "http://pythonec.appspot.com/run"
    result = http_helper2(CODERUN, dict(code=code))
    status = result.get('status')
    if status:
        body = "执行成功:\n" + result.get('out')
    else:
        body = "执行失败:\n" + result.get('err')

    return body

def get_code_types():
    """获取贴代码支持的类型"""
    purl = "http://paste.linuxzen.com/paste"
    def handle(res):
        r = re.compile(r'<option\s+value="(.*?)".*?>(.*?)</option>')
        result = []
        for line in res.readlines():
            if '<option' not in line: continue
            t = dict()
            t['key'], t['value'] = r.findall(line)[0]
            result.append(t)
        return result
    try:
        result = http_helper(purl, callback=handle)
        import string
        t = string.Template("""$key : $value  """)
        r = [t.substitute(v) for v in result]
        result = '\n'.join(r)
    except:
        err_msg = traceback.format_exc()
        logger = get_logger()
        logger.warning(err_msg)
        result = u'代码服务异常,请通知管理员稍候再试'
    return result


def paste_code(poster, typ, codes):
    param = {'class':typ}
    param.update(poster=poster, code = codes, paste="发送")
    purl = "http://paste.linuxzen.com/paste"
    get_url = lambda res:res.url
    try:
        url = http_helper(purl, param, get_url)
    except:
        err_msg = traceback.format_exc()
        logger = get_logger()
        logger.warning(err_msg)
        return False
    if url == purl:
        return False
    else:
        return url


def add_commends(codes, typ, nick):
    commends = {"actionscript": "// ", "actionscript-french" : "// ",
                "ada" : "-- ","apache" : "# ","applescript" : "- ",
                "asm" : "; ","asp" : "// ",  "autoit" : "; ","bash" : "# ",
                "blitzbasic" : "' ","c ":"// ","c_mac" : "// ",
                "cpp" :" // ","csharp" : "// ","css" : ["/* ", " */"],
                "freebasic" : "' ","html4strict" : ["<!-- ", " -->"],
                "java" : "//  ","java5" : "//  ","javascript" : "//  ",
                "lisp" : ";; ","lua" : "--  ","mysql" : "--  ",
                "objc" : "// ","perl" : "# ","php" : "// ",
                "php-brief" : "//  ","python" : "# ","qbasic" : "' ",
                "robots" : "# ","ruby" : "#","sql" : "--  ",
                "tsql" : "-- ","vb" : "'  ","vbnet" : "//  ", "xml":["<!--", "-->"],
                "vim":'"'
               }
    codes  = list(codes)
    symbol = commends.get(typ, '// ')
    if isinstance(symbol, list):
        c = "%s 由Pythoner Club 的 %s 提交\n 欢迎加入我们讨论技术: \
            \n\t使用gtalk添加%s %s\n" % (symbol[0], nick, USER, symbol[1])
    else:
        c = "%s 由Pythoner Club 的 %s 提交\n%s 欢迎加入我们讨论技术: \
            \n%s\t使用gtalk添加%s\n" % (symbol, nick, symbol, symbol, USER)
    c += "#\n#\n####### Code Start #####################\n"
    codes.insert(0, c)
    return codes



class Complex():
    """ add by eleven.i386 """
    def trans(self,content,src=None,dst=None):
        result=""
        def fanyi(a,b,c):

            """ a == src language; b == dst language; c == content """
            c = c.encode('utf-8')
            transurl = 'http://translate.google.com.hk/translate_a/t?client=t&text='
            UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.11 (KHTML, like Gecko) Ubuntu/11.10 Chromium/17.0.963.79 Chrome/17.0.963.79 Safari/535.11'
            r = urllib2.Request(transurl+urllib2.quote(c)+'&hl=zh-CN&sl='+a+'&tl='+b+'&multires=1&prev=btn&ssel=5&tsel=5&sc=1')
            r.add_header('User-Agent',UA)

            d = urllib2.urlopen(r).read()
            return ' '.join(d.split(',')).split(' ')[0].replace('[[[','').replace('"','')

        if isinstance(content,list): # if content include zh-en,ja-zh,zh-ja
            if content[0] in ['zh-en','ja-zh','zh-ja']: # content means : ['zh-en','hello']
                src = content[0].split('-')[0]
                dst = content[0].split('-')[1]
                content = ' '.join(content[1:])
                result = fanyi(src,dst,content)
            elif src == None and dst == None:
                src='en'
                dst='zh'
                content = ' '.join(content)
                result = fanyi(src,dst,content)
        return result

    def tq(self,key):
        key = key.encode('utf-8')
        url = 'http://www.weather.com.cn/data/cityinfo/'
        wordkey = key
        result = urllib.urlopen(url+cityid(wordkey)+'.html')
        load = json.loads(result.read())
        return 'city:%s, Weather %s, %s ~ %s' %(load['weatherinfo']['city'],load['weatherinfo']['weather'],load['weatherinfo']['temp1'],load['weatherinfo']['temp2'])


    def isen(slef,x):
        for i in x:
            if ord(i) < 128:return True
            else:return False


def welcome(frm):
    r = u"欢迎加入我们\n你的昵称是{0}\n可以使用{1}更改你的昵称\n"
    r += u"可以使用help查看帮助"
    r = r.format(frm.local, "-nick")
    return r

def new_member(frm):
    return u"{0} 加入群".format(frm.local)

def get_logger(name = None):
    if not name: name = 'clubot'
    logger = logging.getLogger(name)
    if DEBUG:
        hdl = logging.StreamHandler()
        level = logging.DEBUG
    else:
        hdl = logging.FileHandler(LOGPATH)
        level = logging.INFO
    fmt = logging.Formatter("[%(name)s] %(asctime)s %(levelname)s %(message)s")
    hdl.setFormatter(fmt)
    handler = hdl
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(level) # change to DEBUG for higher verbosity
    logger.propagate = False
    return logger


def get_email(frm):
    try:
        result = frm.bare().as_string()
    except:
        result = frm
    return result



