import requests
import pymongo
from urllib.parse import urlencode
from requests.exceptions import RequestException
import json
from bs4 import BeautifulSoup
import re
from config import *
import os
from hashlib import md5
from multiprocessing import Pool

client = pymongo.MongoClient(MONGO_URL, connect=False)
db = client[MONGO_DB]
#获取列表页面类容
def get_page_index(offset, keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 3
    }
    url = 'http://www.toutiao.com/search_content/?' + urlencode(data)
    response = requests.get(url)
    try:
        if(response.status_code == 200):
            return response.text
        return None
    except RequestException:
        print("列表页请求异常")
        return None
#获取详情页类容
def get_page_detail(url):
    response = requests.get(url)
    try:
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print("详情页请求异常", url)
        return None

#解析列表页文档
def parse_page_index(content):
    data = json.loads(content)
    if data and 'data' in data.keys():
        for item in data.get('data'):
            yield item.get('article_url')

#解析详情页文档
def parse_page_detail(html, url):

    pattern = re.compile('BASE_DATA.galleryInfo =(.*?)</script>.*?', re.S)
    gallery = re.search(pattern, html)
    if gallery:
        title_pattern = re.compile(r'.*?title: \'(.*?)\'.*?', re.S)
        title = re.search(title_pattern, gallery.group(0)).group(1)
        gallery_pattern = re.compile('.*?gallery:\s+(.*?),\s+siblingList.*?')
        gallery_content = re.search(gallery_pattern, gallery.group(0)).group(1)
        data = json.loads(gallery_content)
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:download_image(image)
            return {
                'title': title,
                'url' :url,
                'images': images
            }
#保存到数据库
def save_to_mango(result):
    if db[MONGO_TABLE].insert(result):
        return True
    return False
#下载图片
def download_image(url):
    print("正在下载。。", url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            save_img(response.content)
        return None
    except RequestException:
        print('请求图片出错', url)
        return None

#保存图片
def save_img(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(), md5(content).hexdigest(), 'jpg')
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)
            f.close()
def main(offset):
    html = get_page_index(offset, KEY_WORD)
    for url in parse_page_index(html):
        detail = get_page_detail(url)
        if detail:
            result = parse_page_detail(detail, url)
            if result:
                save_to_mango(result)

if __name__ == '__main__':
    # groups = [x*20 for x in range(GROUP_START, GROUP_END + 1)]
    groups = [1,]
    pool = Pool()
    pool.map(main, groups)