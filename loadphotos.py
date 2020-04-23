import time
import exifread
import re
import requests
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog

__author__ = 'RuanMing'

'''
代码功能：
1.读取所有图片文件的exif信息
2.提取图片中的经纬度，将度、分、秒转换为小数形式
3.利用百度地图API接口将经纬度转换成地址
''' 

JSON_PATH='photos.json'
_n=0  # 读取的文件个数
_ni=0 # 照片的个数
_ng=0 # 存入json的个数

def app_run():
    root = tk.Tk()
    root.withdraw()

    foldpath = filedialog.askdirectory()
    if foldpath.strip() == '':
        return 
    
    photoList = get_pic_GPS(foldpath)
    if len(photoList) != 0:
        with open(JSON_PATH,'w',encoding='utf-8') as fw:
            s = json.dumps(photoList, ensure_ascii=False , indent=4)
            j = 'photos(' + s + ')'
            fw.write(j)
    print('共遍历%s个文件，其中读取%s张照片，并存入json%s张照片。' % (_n,_ni,_ng))

# 遍历文件夹及子文件夹中的所有图片,逐个文件读取exif信息
def get_pic_GPS(pic_dir):
    global _n,_ni, _ng
    photoList = []
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        j = f.read()
    if len(j) > 0:
        photoList = loadJson2()
    items = os.listdir(pic_dir)
    for item in items:
        path = os.path.join(pic_dir, item)
        if os.path.isdir(path):
            get_pic_GPS(path)
        else:
            _n+=1
            suffix = os.path.splitext(item)[1]
            if(suffix=='.jpg' or suffix=='.tif' or suffix=='.jpeg' or suffix=='.JPG' or suffix=='.JPEG' or suffix=='.TIF'):
                _ni += 1
                if pathIsRepeat(photoList,path):
                    continue
                photo = {}
                photo['file_name'] = item
                print(item)
                photo['file_path'] = path
                print(path)
                GPS = imageread(path)
                if GPS == None:
                    continue
                _ng += 1

                photoList.append(dict(photo, **GPS))
                print('+++++++++++++++++++++++')
    return photoList

def loadJson2():
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        jsonp_str = f.read()
    try:
        json_str = re.match('^[^(]*?\((.*)\)[^)]*$', jsonp_str, re.S).group(1)
        return json.loads(json_str)
    except:
        raise ValueError('Invalid JSONP')

def pathIsRepeat(jl, file_path):
    if len(jl) <= 0:
        return False
    for j in jl:
        if j.get('file_path') == file_path:
            return True
    return False


# 将经纬度转换为小数形式
def convert_to_decimal(*gps):
    # 度
    if '/' in gps[0]:
        deg = gps[0].split('/')
        if deg[0] == '0' or deg[1] == '0':
            gps_d = 0
        else:
            gps_d = float(deg[0]) / float(deg[1])
    else:
        gps_d = float(gps[0])
    # 分
    if '/' in gps[1]:
        minu = gps[1].split('/')
        if minu[0] == '0' or minu[1] == '0':
            gps_m = 0
        else:
            gps_m = (float(minu[0]) / float(minu[1])) / 60
    else:
        gps_m = float(gps[1]) / 60
    # 秒
    if '/' in gps[2]:
        sec = gps[2].split('/')
        if sec[0] == '0' or sec[1] == '0':
            gps_s = 0
        else:
            gps_s = (float(sec[0]) / float(sec[1])) / 3600
    else:
        gps_s = float(gps[2]) / 3600

    decimal_gps = gps_d + gps_m + gps_s
    # 如果是南半球或是西半球
    if gps[3] == 'W' or gps[3] == 'S' or gps[3] == "83" or gps[3] == "87":
        return str(decimal_gps * -1)
    else:
        return str(decimal_gps)

# 判断时间先后
def compare_time(time1,time2):
    if time1 <= time2:
        return time1
    else:
        return time2

# 读取图片的经纬度和拍摄时间
def imageread(path):
    f = open(path, 'rb')
    GPS = {}
    try:
        tags = exifread.process_file(f)
        # 读取创建时间和修改时间
        mtime = os.path.getmtime(path)
        ctime = os.path.getctime(path)
        # 确定较早时间
        ftime = compare_time(mtime,ctime)
        # print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(ftime)))
    except:
        return None

    # 南北半球标识
    if 'GPS GPSLatitudeRef' in tags:
        GPS['GPSLatitudeRef'] = str(tags['GPS GPSLatitudeRef'])
        # print(GPS['GPSLatitudeRef'])
    else:
        GPS['GPSLatitudeRef'] = 'N'  # 缺省设置为北半球

    # 东西半球标识
    if 'GPS GPSLongitudeRef' in tags:
        GPS['GPSLongitudeRef'] = str(tags['GPS GPSLongitudeRef'])
        # print(GPS['GPSLongitudeRef'])
    else:
        GPS['GPSLongitudeRef'] = 'E'  # 缺省设置为东半球

    # 获取纬度
    if 'GPS GPSLatitude' in tags:
        lat = str(tags['GPS GPSLatitude'])
        # 处理无效值
        if lat == '[0, 0, 0]' or lat == '[0/0, 0/0, 0/0]':
            return None

        deg, minu, sec = [x.replace(' ', '') for x in lat[1:-1].split(',')]
        # 将纬度转换为小数形式
        GPS['GPSLatitude'] = convert_to_decimal(deg, minu, sec, GPS['GPSLatitudeRef'])
        print(GPS['GPSLatitude'])

    # 获取经度
    if 'GPS GPSLongitude' in tags:
        lng = str(tags['GPS GPSLongitude'])

        # 处理无效值
        if lng == '[0, 0, 0]' or lng == '[0/0, 0/0, 0/0]':
            return

        deg, minu, sec = [x.replace(' ', '') for x in lng[1:-1].split(',')]
        # 将经度转换为小数形式
        GPS['GPSLongitude'] = convert_to_decimal(deg, minu, sec, GPS['GPSLongitudeRef'])  # 对特殊的经纬度格式进行处理
        print(GPS['GPSLongitude'])

    # 获取图片拍摄时间
    if 'Image DateTime' in tags:
        str_t = str(tags["Image DateTime"])
        if str_t == '':
            GPS["DateTime"] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(ftime))
        else:
            tmp_t = time.mktime(time.strptime(str_t, '%Y:%m:%d %H:%M:%S'))
            GPS["DateTime"] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(compare_time(tmp_t, ftime)))
    elif "EXIF DateTimeOriginal" in tags:
        str_t = str(tags["EXIF DateTimeOriginal"])
        if str_t == '':
            GPS["DateTime"] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(ftime))
        else:
            tmp_t = time.mktime(time.strptime(str_t, '%Y:%m:%d %H:%M:%S'))
            GPS["DateTime"] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(compare_time(tmp_t, ftime)))
    else:
        GPS["DateTime"] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(ftime))
    print(GPS["DateTime"])

    # 获取图片相机类型
    if 'Image Make' in tags:
        GPS["Image Make"] = str(tags['Image Make'])
        print('照相机制造商：', GPS["Image Make"])
    if 'Image Model' in tags:
        GPS["Image Model"] = str(tags['Image Model'])
        print('照相机型号：', GPS['Image Model'])
    
    return GPS

if __name__ == "__main__":
    app_run()