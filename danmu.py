# -*- coding: utf-8 -*-
#/usr/bin/env python
#Author:Neo
#Email:zealzpc@gmail.com
import tornado.ioloop
import tornado.gen as gen
from tornado.httpclient import AsyncHTTPClient,HTTPRequest
import json
from optparse import OptionParser
import platform
from tornado.tcpclient import TCPClient
from tornado.options import define, options
import time
import random

CHATINFOURL = 'http://riven.panda.tv/chatroom/getinfo?roomid='
IGNORE_LEN = 12
META_LEN = 4
CHECK_LEN = 4
FIRST_REQ = b'\x00\x06\x00\x02'
FIRST_RPS = b'\x00\x06\x00\x06'
KEEPALIVE = b'\x00\x06\x00\x00'
RECVMSG = b'\x00\x06\x00\x03'
DANMU_TYPE = '1'#普通弹幕
BAMBOO_TYPE = '206'#送竹子
AUDIENCE_TYPE = '207'#在线人数
TU_HAO_TYPE = '306'#连击
BOARD_CAST = '311'#平台礼物广播
SYSINFO = platform.system()
INIT_PROPERTIES = 'init.properties'
MANAGER = '60'
SP_MANAGER = '120'
HOSTER = '90'
WWW = 'www'
aaa = 'aaa'
camera_token = ''
expire_time = time.time()
last_contral = time.time()-7


async def KeepAlive(s):
    print('======start keepalive======')
    while True:
        await s.write(KEEPALIVE)
        await gen.sleep(150)


async def formatMsg(recvMsg):
    jsonMsg = eval(recvMsg)
    content = jsonMsg['data']['content']
    #print('type',jsonMsg['type'],sep=':')
    #if jsonMsg['type'][0] != DANMU_TYPE:
    print('='*20)
    print('data:',json.dumps(jsonMsg))
    #    #print(jsonMsg,file='%s.log'%options.roomid)
    #with open('%s.log'%options.roomid,'at') as log:
    #    log.write(json.dumps(jsonMsg)+'\n')
    if jsonMsg['type'] == DANMU_TYPE:
        print("==============收到一条普通弹幕================")
        identity = jsonMsg['data']['from']['identity']
        nickName = jsonMsg['data']['from']['nickName']
        rid = jsonMsg['data']['from']['rid']
        spIdentity = jsonMsg['data']['from']['sp_identity']
        if spIdentity == SP_MANAGER:
            nickName = '*超管*' + nickName
        if identity == MANAGER:
            nickName = '*房管*' + nickName
        if identity == HOSTER:
            nickName = '*主播*' + nickName
        #识别表情
        #emoji = re.match(r"(.*)\[:(.*)](.*)", content)
        #if emoji:
        #    content = emoji.group(1) + '*' + emoji.group(2) + '*' + emoji.group(3)
        #print('='*20)
        print(nickName + ":" + content)
        #notify(nickName, content)
        print('rid:%s'%rid)
        print('content:%s'%content)

    elif jsonMsg['type'] == BAMBOO_TYPE:
        #print("data:%s"%recvMsg)
        nickName = jsonMsg['data']['from']['nickName']
        #print(nickName + "送给主播[" + content + "]个竹子")
        #notify(nickName, "送给主播[" + content + "]个竹子")
    elif jsonMsg['type'] == TU_HAO_TYPE:
        #print("data:%s"%recvMsg)
        print('====tuhao===========')
        nickName = jsonMsg['data']['from']['nickName']
        rid = jsonMsg['data']['from']['rid']
        headimg = jsonMsg['data']['content']['avatar']
        price = int(jsonMsg['data']['content']['price'])
        print('*********%s送给主播%s个%s 价值:%s**********'%(nickName,
                                                             jsonMsg['data']['content']['count'],
                                                             jsonMsg['data']['content']['name'],
                                                             jsonMsg['data']['content']['price']

                                                                       ))
    else:
        pass


async def getChatInfo(roomid):
    url = CHATINFOURL + roomid
    http_client = AsyncHTTPClient()
    res = await http_client.fetch(url)
    chatInfo = json.loads(res.body)
    chatAddr = chatInfo['data']['chat_addr_list'][0]
    socketIP,socketPort = chatAddr.split(':')
    print('chat ip:',socketIP)
    print('chat port:',socketPort)
    stream = await TCPClient().connect(socketIP, socketPort)
    rid      = str(chatInfo['data']['rid']).encode('utf-8')
    appid    = str(chatInfo['data']['appid']).encode('utf-8')
    authtype = str(chatInfo['data']['authType']).encode('utf-8')
    sign     = str(chatInfo['data']['sign']).encode('utf-8')
    ts       = str(chatInfo['data']['ts']).encode('utf-8')
    msg  = b'u:' + rid + b'@' + appid + b'\nk:1\nt:300\nts:' + ts + b'\nsign:' +     sign + b'\nauthtype:' + authtype
    msgLen = len(msg)
    sendMsg = FIRST_REQ + int.to_bytes(msgLen, 2, 'big') + msg
    await stream.write(sendMsg)
    recvMsg = await stream.read_bytes(CHECK_LEN)
    if recvMsg == FIRST_RPS:
        print('成功连接弹幕服务器')
        recvLen = int.from_bytes(await stream.read_bytes(2), 'big')
        await stream.read_bytes(recvLen)
    ioloop.call_later(0,KeepAlive,stream)

    while True:
        recvMsg = await stream.read_bytes(CHECK_LEN)
        if recvMsg == RECVMSG:
            recvLen = int.from_bytes(await stream.read_bytes(2), 'big')
            recvMsg = stream.read_bytes(recvLen)   #ack:0
            totalLen = int.from_bytes(await stream.read_bytes(META_LEN), 'big')
            try:
                await analyseMsg(stream, totalLen)
            except Exception as e:
                pass

async def analyseMsg(s, totalLen):
    while totalLen > 0:
        await s.read_bytes(IGNORE_LEN)
        recvLen = int.from_bytes(await s.read_bytes(META_LEN),'big')
        recvMsg = await s.read_bytes(recvLen)
        # recv the whole msg.
        while recvLen > len(recvMsg):
            recvMsg = b''.join(recvMsg, s.recv(recvLen - len(recvMsg)))
        await formatMsg(recvMsg)
        totalLen = totalLen - IGNORE_LEN - META_LEN - recvLen


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-l", "--roomid", dest="roomid",
                  help="roomid")
    (options, args) = parser.parse_args()
    print('options:',options)
    ioloop = tornado.ioloop.IOLoop.current()

    #ioloop.call_later(0,contral_camera,'787552313',2,0,2)
    #print('run request') 

    ioloop.call_later(3,getChatInfo,options.roomid)
    ioloop.start()
#
