# -*- coding:utf-8 -*-

"""
 * @autor:zhangguodong
 * @Time:2018/8/20
 * @File: ftpFiles_Download.py
 * @Function：***下载ftp://ftp2.dlink.com网址上的固件**
 * @Description
"""


import os
import sys
import ftplib
import timeit
import multiprocessing


class FTPSync(object):
    def __init__(self):
        ###域名（或主机地址）、用户名、密码
        self.conn = ftplib.FTP('ftp2.dlink.com', 'anonymous', 'anonymous@example.com')
        self.conn.cwd('BETA_FIRMWARE/')     # 远端FTP目录
        os.chdir('E:\\dlink')               # 本地下载目录


    def get_dirs_files(self):
        u''' 得到当前目录和文件, 放入dir_res列表 '''
        dir_res = []
        self.conn.dir('.', dir_res.append)
        files = [f.split(None, 8)[-1] for f in dir_res if f.startswith('-')]
        dirs = [f.split(None, 8)[-1] for f in dir_res if f.startswith('d')]
        return (files, dirs)


    def walk(self, next_dir):
        # print 'Walking to', next_dir
        self.conn.cwd(next_dir)
        try:
            os.mkdir(next_dir)
        except OSError:
            pass
        l = os.chdir(next_dir)



        ftp_curr_dir = self.conn.pwd()
        local_curr_dir = os.getcwd()
        files, dirs = self.get_dirs_files()
        #print "FILES: ", files
        #print "DIRS: ", dirs
        for f in files:
            #print next_dir, ':', f
            print 'download :',os.path.abspath(f)
            outf = open(f, 'wb')
            try:
                self.conn.retrbinary('RETR %s' % f, outf.write)
            finally:
                outf.close()
        for d in dirs:
            os.chdir(local_curr_dir)#切换本地的当前工作目录为d的父文件夹
            self.conn.cwd(ftp_curr_dir)#切换ftp的当前工作目录为d的父文件夹
            self.walk(d) #在这个递归里面，本地和ftp的当前工作目录都会被更改


    def run(self):
        self.walk('.')


def main():
    f = FTPSync()
    f.run()


if __name__ == '__main__':
    start = timeit.default_timer()

    pool = multiprocessing.Pool(8)
    # for i in range(20):
    #     pool.apply_async(func = begin,args=('Process'+str(i),))
    pool.apply(func = main )
    pool.close()
    pool.join()

    end = timeit.default_timer()
    print str(end - start)