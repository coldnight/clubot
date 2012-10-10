#!/usr/bin/python
#coding=utf-8

import sys 
import json 
import urllib
import urllib2
from city import cityid

class Complex():
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
