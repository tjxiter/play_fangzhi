#!/usr/bin/python
#coding:UTF-8

import sys
sys.path.append('.')
sys.path.append('../')
reload(sys)
sys.setdefaultencoding("utf-8")
import time
import urllib2
import re
import json

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from openpyxl import Workbook


all_items = ["City", "Fax", "Country/Region", "Company", "name", "Zip", "Telephone", "Mobile Phone", "Address", "Province/State", "main_markets"]

def crawl_all(source_file, destination_file, continue_file):

    f = open(source_file, 'r')
    ffprofile = webdriver.FirefoxProfile('/Users/tjx/Library/Application Support/Firefox/Profiles/tiffgp2i.default')
    driver = webdriver.Firefox(firefox_profile=ffprofile)
    driver.set_page_load_timeout(20)
    driver.get('http://www.alibaba.com')

    cc = None
    # get continue point
    fc = open(continue_file, 'r')
    for one in fc.readlines():
        cc = one
        break
    fc.close()

    go = False # True：才开始爬联系方式
    # 第一次需要手动输入密码
    cnt = 1

    conss = []
    for one in f.readlines():
        if go == False:
            if not cc:
                go = True
            elif one == cc:
                go = True
            else:
                continue

        if go:
            cons = crawl_ali_contact(driver, one)
            print cnt
            if cnt == 1:
                time.sleep(20)
            else:
                time.sleep(5)

            cnt += 1
            if cons is not None:
                conss.append(cons)
                print cons
                f = open(destination_file, 'a')
                f.write('''%s\n''' % json.dumps(cons))

                if len(one) > 20:
                    fc = open(continue_file, 'w')
                    fc.write(one)
        '''
        # 保存为csv
        # create_csv(conss)

        #保存文件
        text = ''
        for one in conss:
            text = '%s\n%s' % (text, one)

        f = open(destination_file, 'a')
        f.write(text)
        '''
    f.close()
    fc.close()


def crawl_ali_contact(driver, url):

    t1 = time.time()
    print url
    try:
        driver.get(url)
        page = driver.page_source

        t2 = time.time()
        print 't2-t1: %s' % (t2-t1)

        soup = BeautifulSoup(page, "lxml")
        t3 = time.time()
        print 't3-t2: %s' % (t3-t2)

        contact_url = soup.find('td', {'class': 'action-contact'}).a.get('href')
        print 'contact_url: %s' % contact_url

        cons = get_contact(driver, contact_url)
        cons['main_markets'] = get_market(driver, page, url)

        return cons

    except TimeoutException:
        print 'timeout..............'
        return None
    except Exception, e:
        print e
        return None


def get_market(driver, page, url):

    dp1 = page.find('dmtrack_pageid')
    pe1 = page.find('productEncryptId')
    print dp1, pe1
    if dp1 == -1 or pe1 == -1:
        return url

    p1 = page.find("'", dp1 + 15)
    p2 = page.find("'", dp1 + 16)
    dmtrack_pageid = page[p1+1:p2]

    e1 = page.find("'", pe1 + 18)
    e2 = page.find("'", pe1 + 20)
    productEncryptId = page[e1+1:e2]

    market_url = 'https://www.alibaba.com/core/CommonSupplierBasicInformationWidget/view.json?productEncryptId=%s&dmtrack_pageid=%s' % (productEncryptId, dmtrack_pageid)
    print 'market_url: %s' % market_url
    driver.get(market_url)
    soup = BeautifulSoup(driver.page_source, "lxml")

    top =soup.find('tr', {'data-role': 'companyMainMarket'}).findAll('span')

    lens = len(top)
    kk = [str(top[i].text)for i in range(lens) if (i+1)%2]
    vv = [str(top[i].text) for i in range(lens) if (i+2)%2]

    values = {}
    for i in range(lens/2):
        values[kk[i]] = vv[i]

    print values

    return json.dumps(values)


def get_contact(driver, con_url):

    if con_url is None:
        return None
    try:
        driver.get(con_url)
        soup = BeautifulSoup(driver.page_source, "lxml")
        info = {}
        overview = soup.find('div', {'class': 'contact-overview'}).find('div', {'class': 'contact-info'})

        info["Company"] = str(soup.find('table', {'class': 'company-info-data table'}).findAll('tr')[0].findAll('td')[-1].text)
        info["name"] = str(overview.h1.text.strip())
        details = soup.find('div', {'class': 'contact-detail'})

        k = details.findAll('dt')
        v = details.findAll('dd')
        for i in range(len(k)):
            info[str(k[i].text[:-1])] = str(v[i].text) if v[i].text else "None"

        com = con_url.split('//')[1].split('.')[0]
        accountId = soup.find('div', {'class': 'contact-detail-mask'}).a.get('data-account-id')
        phone_url = 'https://%s.en.alibaba.com/event/app/contactPerson/showContactInfo.htm?encryptAccountId=%s' % (com, accountId)

        print phone_url
        driver.get(phone_url)
        soupp = BeautifulSoup(driver.page_source, "lxml")

        info["Telephone"] = json.loads(soupp.find('pre').text)['contactInfo']['accountFax']
        info["Fax"] = json.loads(soupp.find('pre').text)['contactInfo']['accountMobileNo']
        info["Mobile Phone"] = str(json.loads(soupp.find('pre').text)['contactInfo']['accountPhone'])

        global all_items
        for one in all_items:
            if one not in info:
                info[one] = "None"
    except TimeoutException:
        return None

    return info


def create_csv(data, file_name="tmp.csv"):

    wb = Workbook()
    ws = wb.active

    ws.append(all_items)

    for one in data:
        r = []
        for k, v in one.items():
            r.append(v)
        ws.append(r)

    ws.column_dimensions['D'].width = 80
    wb.save(file_name)


if __name__ == "__main__":
    crawl_all('sample.txt')
