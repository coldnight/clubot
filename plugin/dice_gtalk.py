#!/usr/bin/python
# -*- coding: utf-8 -*-

#import pydcop
#import sys
#import os
#import random
#import dice
import random


def strGetLastNumber(szExp):
    szExp=" " + szExp.strip()
    for i in range(len(szExp)-1,-1,-1):
        if(szExp[i]<'0' or szExp[i]>'9'):
            break
        #end if
    #next i
    szExp=szExp + " "
    if(len(szExp)-i-2==0):
        return [0,0]
    return [int(szExp[i+1:len(szExp)].strip()),len(szExp)-i-2]

#end function

def strGetFirstNumber(szExp):
    szExp=szExp.strip() + ' '
    for i in range(0,len(szExp)):
        if(szExp[i]<'0' or szExp[i]>'9'):
            break
        #end if
    #next i
    szExp='0' + szExp.strip()
    return [int(szExp[0:i+1]),i]



def DiceExpress(expre):

    try:
        exp=expre.lower().strip()

        dPos=exp.find('d')
        while(dPos!=-1):

            tmpList=strGetLastNumber(exp[:dPos])
            iDiceCount=int(tmpList[0])
            iDataWidth_Preview=int(tmpList[1])


            tmpList=strGetFirstNumber(exp[dPos+1:])
            iDiceFace=int(tmpList[0])
            iDataWidth_Next=int(tmpList[1])

            tmpExp=''

            if(iDiceCount==0):
                iDiceCount=1
            if(iDiceFace==0 and iDataWidth_Next==0):
                iDiceFace=20

            for i in range(1,iDiceCount+1):
                tmp=random.randint(1,iDiceFace)
                tmpExp=tmpExp + str(tmp) + '+'

            tmpExp=tmpExp.rstrip('+')
            tmpExp="(" + tmpExp + ")"

            exp=exp[0:dPos-iDataWidth_Preview] + tmpExp + exp[dPos+iDataWidth_Next+1:]


            dPos=exp.find('d')
        #wend
        return exp
    except:
        pass


def roll(command):

    command=command.replace('　',' ')
    command=command.replace('。','.')
    command=command.replace('Ｒ','r',1)
    command=command.strip() + '\n'

    nPos=command.find('\n')


    if(nPos==-1):
        nPos=len(command)


    while(nPos!=-1):

        szTmpCmd=command[:nPos]
        if(szTmpCmd.lower()[0:2]=='.r' or szTmpCmd.lower()[0:2]=='/r'):
            szTmpCmd=szTmpCmd[2:].strip()

        sPos=-1
        sPos=szTmpCmd.find(' ')
        if(sPos==-1):
            sPos=len(szTmpCmd)
        szExpress=szTmpCmd[:sPos].strip().lower()
        szInfo=szTmpCmd[sPos:].strip()
        tmp=szExpress.lower().strip()
        szExpress=DiceExpress(szExpress)

        outMsg="进行" + szInfo + "检定,结果:" + tmp + "=" + szExpress + "=" + str(eval(szExpress))


        command=command[nPos+1:]
        nPos=command.find('\n')
        return outMsg

    #wend
if __name__ == '__main__':
    import sys
    print roll(' '.join(sys.argv[1:]))
