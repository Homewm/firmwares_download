# -*- coding:utf-8 -*-

'''
author: zgd
time: 2019.06.03
function：针对mongoDB数据库中的固件url进行批量化下载的工具
说明：首先每个数据都需要插入一行，设置status为0状态。下载成功status设置为1状态。大文件status设置为2，下载不成功status设置为3。
异常：有很多时候会出现异常，主要在于url编码的问题上。后面都进行了备注。
'''


import multiprocessing
import pymongo
import os
import urllib2
import urllib
import time
import timeit
import string
import argparse
import sys
import re
import urlparse
import socket
#get mongodb info
import codecs
import ConfigParser

reload(sys)
sys.setdefaultencoding('utf-8')


'''通过scrapy.cfg配置文件确定下载位置'''
# config = ConfigParser.ConfigParser()
# configfile = r'./scrapy.cfg'
# config.readfp(codecs.open(configfile,'r','utf-8'))
# ##IP
# MONGO_URI = config.get('mongo_cfg',"MONGO_IP")
# ##端口
# MONGO_PORT = config.get('mongo_cfg',"MONGO_PORT")
# ##数据库名
# MONGO_DATABASE = config.get('mongo_cfg',"MONGO_DATABASE")
# ##数据集名
# MONGO_COLLECTION = config.get('mongo_cfg',"MONGO_SCRAPY_COLLECTION_NAME")
# ##下载保存的路径
# dirs_root = config.get('other_cfg',"DOWNLOAD_DIR")


'''通过直接配置位置信息获取固件信息'''
##IP
MONGO_URI = "10.10.12.19"
##端口
MONGO_PORT = "27017"
##数据库名
MONGO_DATABASE = "firmwareWebInfo_zgd"
##数据集名
MONGO_COLLECTION = "zgd_total_dataset"
##下载保存的路径
dirs_root = "/home/ubuntu/disk/hdd_3/zgd/firmwares_zgd"



'''通过参数确定固件下载的位置'''
# parser = argparse.ArgumentParser(description = "Firmware batch download with firmware url")
# parser.add_argument("-ip","--mongo_URI", required= True, help = "input mongo ip")
# parser.add_argument("-p","--mongo_port", required= True, help = "input mongodb ip port")
# parser.add_argument("-db","--mongo_database", required= True, help = "input mongodb database name")
# parser.add_argument("-c","--mongo_collection", required= True, help = "input ip mongo collection")
# parser.add_argument("-o", "--output", required = True, help = "Output Result File Name (no spaces)")
#
# args = vars(parser.parse_args())
#
# ##IP
# MONGO_URI = args['mongo_URI']
# ##端口
# MONGO_PORT = args['mongo_port']
# ##数据库名
# MONGO_DATABASE = args['mongo_database']
# ##数据集名
# MONGO_COLLECTION = args['mongo_collection']
# ##下载保存的路径
# dirs_root = args['output']


filesize = 500 # 默认文件大小是400M
filesize= int(filesize)


conn = pymongo.MongoClient(MONGO_URI,int(MONGO_PORT),maxPoolSize=None)
##链接数据库
db = conn.get_database(MONGO_DATABASE)
##链接数据集
collection = db.get_collection(MONGO_COLLECTION)

# 加header，模拟浏览器
header = {'User-Agent': "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0",
          'Accept': 'image/webp,*/*',
          'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
          'Accept-Encoding': 'gzip, deflate, br',
          'Connection': 'keep-alive'
          }


def get_filename(url):
    '''获取真实的固件名称，通过文件下载时获取'''

    filename = ""
    '''下面这就话有时加，有时不加'''
    # url = urllib.quote(url, safe=string.printable)  ###处理有些含中文的情况
    url = url.encode('utf-8')
    try:
        url = urllib.quote(url.encode('utf8'), ':/')  ###有些需要使用utf8文件名编码，不然无法下载
        req = urllib2.urlopen(url, timeout = 60)
        # 下载时，响应头中指定了文件名
        if req.info().has_key('Content-Disposition'):
            file_Name_1 = req.info()['Content-Disposition'].split('filename=')  #常出现的结果
            file_Name_2 = req.info()['Content-Disposition'].split('filename*=')  #onkyo厂商这种会出现这样的结果
            file_Name_3 = req.info()['content-disposition'].split('filename=')  # 不知道是否区分大小写
            if len(file_Name_1) >=2:
                try:
                    print "file_Name_1", file_Name_1
                    file_name = file_Name_1[1]
                    print file_name
                    ##重定向时filename文件名中含有双引号问题
                    # filename = filename.repalce('"','').replace("'", "")
                    if '\"' in file_name:
                        patern = re.compile(r'"(.*)"')
                        filename = patern.findall(file_name)[0]
                    else:
                        filename = file_name   ##当然也存在一些没有双引号的问题
                except Exception, e:
                    print "->1", e.message
            elif len(file_Name_3) >=2:
                try:
                    file_name = file_Name_1[1]
                    ##重定向时filename文件名中含有双引号问题
                    # filename = filename.repalce('"','').replace("'", "")
                    patern = re.compile(r'"(.*)"')
                    if '\"' in file_name:
                        patern = re.compile(r'"(.*)"')
                        filename = patern.findall(file_name)[0]
                    else:
                        filename = file_name   ##当然也存在一些没有双引号的问题
                except Exception,e:
                    print "->3", e.message
            elif len(file_Name_2) >=2:     ###针对onkyo厂商的处理
                try:
                    filename = file_Name_2[1].split('UTF-8\'\'')[-1].strip()
                except Exception,e:
                    print "->2", e.message
            elif url:
                filename = os.path.basename(url)
        # 下载时，url重定向或是url中带有文件名
        elif req.info().has_key('Content-Length'):
            filename = url.split('/')[-1]
        elif req.url != url:
            filename = os.path.basename(urlparse.urlsplit(req.url)[2])
        else:
            filename = os.path.basename(url)
        print filename   ###获取固件名称
    except Exception,e:
        print "--> get_filename Error:",e
    return filename


# ##处理进度条
# def cbk(a,b,c):
#     '''回调函数
#     @a:已经下载的数据块
#     @b:数据块的大小
#     @c:远程文件的大小
#     '''
#     per=100.0*a*b/c
#     if per>100:
#         per=100
#     print '%.2f%%' % per


def url_deal(url):
    '''处理类类似于http://www.wayos.com/../Upfiles/down/WAP_3048-18.07.04V.trx链接不能下载的问题'''
    if "/../" in url:
        url = url.replace('/../','/\.\./')
    return url


def download(cur):
    '''
    针对mongo数据库中的每条url进行下载。
    其中未使用的url状态status标记为0，已下载标记为1，大文件标记为2，无法下载标记为3
    '''
    name = cur['firmwareName']  # 把固件名赋值给name
    url = cur['url'].strip()  ###有的有空格

    url = url_deal(url)

    ##处理一下

    '''处理含中文常用的几个start'''
    # url = urllib.quote(url, safe=string.printable)  ###处理有些含中文的情况
    url = urllib.quote(url.encode('utf8'), ':/')   ###有些需要使用utf8文件名编码，不然无法下载
    '''end'''

    # url = urllib.quote_plus(url, safe="")
    # url = urllib.unquote(url)
    # url = url.decode('utf-8').encode('gbk')

    manufacturer = cur['manufacturer']  # 把firm赋值给firmname
    filename = get_filename(url)  # 真实的固件文件名，下载获取到
    dirs = os.path.join(dirs_root, manufacturer)  #在FIRMWARE下根据厂商名建立新文件夹
    if not os.path.exists(dirs):
        os.makedirs(dirs)
    filePath = os.path.join(dirs, filename)  # 定义文件的绝对路径，含文件名
    timeModel = '%Y-%m-%d'

    # 判断文件是否已经存在，若不存在，继续下载，若存在，输出路径不下载
    if os.path.exists(filePath):
        if os.path.getsize(filePath) > 1:
            print url
            print filePath, '文件已经存在'  # 已经下载过的文件，修改status值
            collection.update({'_id': cur['_id']}, {
                "$set": {
                    'status': 1,
                    'filename': filename,
                    # 'firmwareSize': os.path.getsize(filename),  # 取大小
                    'downloadTime': time.strftime(timeModel, time.localtime())}})
            return


    trytime = 3
    while trytime > 0:
        try:
            '''下面这个有时加，有时不加'''
            # url = urllib.quote(url.encode('utf8'), ':/')  ###有些需要使用utf8文件名编码，不然无法下载
            res = urllib2.urlopen(urllib2.Request(url, None, header), timeout=120)
            try:
                fsize = 1
                try:
                    if res.headers["content-length"]:
                        fsize = res.headers["content-length"]
                    elif res.headers["Content-Length"]:
                        fsize = res.headers["Content-Length"]
                except Exception,e:
                    print "content-length is not exist!",e.message
                fsize = long(fsize)
                file_size = fsize / float(1024 * 1024)
                file_size = round(file_size, 2)
                print "url:", url
                print "文件大小为：", file_size, "M"
                # fsize = int(fsize)
                if int(file_size) < filesize:
                    try:
                        urllib.urlretrieve(url, filePath)
                    except socket.timeout:
                        count_time = 1
                        while count_time <=5:
                            try:
                                urllib.urlretrieve(url, filePath)
                                break
                            except socket.timeout:
                                count_time += 1
                        if count_time >5:
                            print "下载不成功", url
                    # os.rename(filename,filename)
                    #with open(filename, 'wb') as f:
                    #    f.write(res.read())
                    #    f.close()

                    collection.update({'_id': cur['_id']}, {
                        "$set": {
                            'status': 1,
                            'filename': filename,
                            # 'firmwareSize': os.path.getsize(filename),  # 取大小
                            'downloadTime': time.strftime(timeModel, time.localtime())}})  # 取时间
                    print"第一次修改成功"

                else:
                    #status 2 for big file 文件较大
                    collection.update({'_id': cur['_id']}, {
                        "$set": {
                            'status': 2,
                            'filename': filename,
                            'downloadTime': time.strftime(timeModel, time.localtime())
                        }})
                break

            except Exception, e:
                print "固件下载失败1：", e.message
                print "url: ", url
        except Exception, e:
            print "固件下载失败2：", e.message
            print "url: ", url
            trytime -= 1

    #status download failed for net or other 5次尝试文件都未下载成功
    collection.update(
        {"_id": cur['_id']}, {
            "$set": {
                'status': 3,
                'filename': filename,
                'downloadTime': time.strftime(timeModel, time.localtime())
                }})
    return


'''暂时未用'''
def insert_mongo_status():
    collection.update({},{"$set":{'status':0}},false,true)
    return


def multiprocess():
    # pool = multiprocessing.Pool(processes=32)
    try:
        print db
        print collection

        if collection.find({'status':0}).count() > 0:   ###需要首先在数据集中添加一列，标记为status：0状态
            flist = list(collection.find({"status":0}))
            for tr_list in flist:   ###其中tr_list为一个固件的所有信息
            #     # print "tr_list", tr_list
            #     # print tr_list['url']
                download(tr_list)
            #     pool.apply_async(download, (tr_list, ))
            # pool.close()
            # pool.join()
            print "sub-process status 0 done"
        else:
            return 0
    except Exception, e:
        print e



if __name__ == "__main__":
    start_time = timeit.default_timer()
    ###执行程序
    multiprocess()
    end_time = timeit.default_timer()
    time_use = str(end_time - start_time)
    timeArray_1 = time.localtime(start_time)
    format_startTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray_1)
    timeArray_2 = time.localtime(end_time)
    format_endTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray_2)

    print "===================================="
    print "程序运行开始时间点：", format_startTime
    print "程序运行结束时间点：", format_endTime
    print "程序运行时间：", time_use
    print "====================================="



