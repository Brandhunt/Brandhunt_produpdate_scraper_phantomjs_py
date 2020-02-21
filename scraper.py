#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#  /|\/|\/|\/|\/|\/|\/|\/|\/|\/|\/|\/|\/|\/|\/|\  
# <   -  Brandhunt Product Update Scraper   -   >
#  \|/\|/\|/\|/\|/\|/\|/\|/\|/\|/\|/\|/\|/\|/\|/

# --- IMPORT SECTION --- #

import os
os.environ['SCRAPERWIKI_DATABASE_NAME'] = 'sqlite:///data.sqlite'

import scraperwiki
from lxml import etree
import lxml.html
import requests
import json
import base64
#import mysql.connector
import re
###import random
from selenium import webdriver
###from seleniumwire import webdriver
#from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from slugify import slugify
from splinter import Browser
import sys
import time
import traceback
from translate import Translator
#from urllib2 import HTTPError
from urllib.error import HTTPError
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

# --- CURRENT FILE EXPORT SECTION --- #

#scraperwiki.sqlite.execute("drop table if exists modstoexport")
#scraperwiki.sqlite.execute("drop table if exists modulstoexport")
#scraperwiki.sqlite.execute("drop table if exists modulestoexport")
#scraperwiki.sqlite.execute("drop table if exists filustoexport")
#scraperwiki.sqlite.commit()

with open(__file__, 'r') as file:
    try:
        ###file_text = '' + ''.join(file.readlines()) + ''
        #file_text = json.dumps(file.readlines())
        ###file_id = '1'
        ###scraperwiki.sqlite.save(table_name = 'modstoexport', unique_keys=['modid'], data={'modid': file_id, 'mod': file_text})
        file_text = json.dumps(file.readlines())
        filusid = '1'
        scraperwiki.sqlite.save(table_name = 'filestoexport', unique_keys=['file_id'], data={'file_id': filusid, 'file_cont': file_text})
        print('Current file module export successful!')
    except:
        print(traceback.format_exc())
    
# --- FUNCTION SECTION --- #

# *** --- Replacement for PHP's array merge functionality --- *** #
def array_merge(array1, array2):
    if isinstance(array1, list) and isinstance(array2, list):
        return array1 + array2
    elif isinstance(array1, dict) and isinstance(array2, dict):
        return dict(list(array1.items()) + list(array2.items()))
    elif isinstance(array1, set) and isinstance(array2, set):
        return array1.union(array2)
    return False

# *** --- For checking if a certain product attribute exists --- *** #
def doesprodattrexist(prodattrlist, term, taxonomy):
    for prodattr in prodattrlist:
        if prodattr['term_id'] == term or prodattr['name'] == term or prodattr['slug'] == term:
            return prodattr
    return 0
    
# *** --- Custom substitute for adding together attributes variables --- *** #
def add_together_attrs(attrlist1, attrlist2, prodattr):
    newattrs=list((a for a in attrlist1 if a[0]['term_id'] == -1))
    oldattrs=list((a[0]['term_id'] for a in attrlist1 if a[0]['term_id'] > -1))
    attrlist2=list((a[0]['term_id'] for a in attrlist2))
    #print('newattrs: ' + json.dumps(list(newattrs)))
    #print('oldattrs: ' + json.dumps(list(oldattrs)))
    #filtattrs = oldattrs + attrlist2
    filtattrs = list(set(oldattrs) | set(attrlist2)) 
    #print('filtattrs: ' + json.dumps(list(filtattrs)))
    for flt in filtattrs:
        flt = doesprodattrexist(jsonprodattr[prodattr], flt, prodattr)
        if flt != 0:
            newattrs.append((flt, False))
    #print('finalattr: ' + json.dumps(list(finalattr)))
    return newattrs
    
# *** --- For getting proper value from scraped HTML elements --- *** #
def getmoneyfromtext(price):
    val = re.sub(r'\.(?=.*\.)', '', price.replace(',', '.'))
    if not val: return val
    else: return '{:.0f}'.format(float(re.sub(r'[^0-9,.]', '', val)))
    
# *** --- For converting scraped price to correct value according to wanted currency --- *** #
def converttocorrectprice(price, currencysymbol):
    r = requests.get('https://api.exchangeratesapi.io/latest?base=' + currencysymbol + '', headers=headers)
    json = r.json()
    jsonrates = json['rates']
    foundinrates = False
    for ratekey, ratevalue in jsonrates.items():
        if price.find('' + ratekey + '') != -1:
            price = price.replace(r'[^0-9,.]', '')
            price = getmoneyfromtext(price)
            #print('CURRENCY: ' + currencysymbol)
            #print('PRICE: ' + price)
            #print('RATEKEY: ' + ratekey)
            #print('RATEVALUE: ' + str(ratevalue))
            price = float(price) / ratevalue
            price = getmoneyfromtext(str(price))
            foundinrates = True
            break
    if not foundinrates:
        if price.find(u'$') != -1:
            price = price.replace(r'[^0-9,.]', '')
            price = getmoneyfromtext(price)
            price = float(price) / jsonrates['USD']
            price = getmoneyfromtext(str(price))
        elif price.find(u'£') != -1:
            price = price.replace(r'[^0-9,.]', '')
            price = getmoneyfromtext(price)
            price = float(price) / jsonrates['GBP']
            price = getmoneyfromtext(str(price))
        elif price.find(u'€') != -1:
            price = price.replace(r'[^0-9,.]', '')
            price = getmoneyfromtext(price)
            price = float(price) / jsonrates['EUR']
            price = getmoneyfromtext(str(price))
        else:
            price = price.replace(r'[^0-9,.]', '')
            price = getmoneyfromtext(price)
    #print("CONVERTEDPRICE:" + price)
    return price

# *** --- For grabbing URLs from text-based values/strings --- *** #
def graburls(text, imageonly):
    try:
        imgsuffix = ''
        if imageonly:
            imgsuffix = '\.(gif|jpg|jpeg|png|svg|webp)'
        else:
            imgsuffix = '\.([a-zA-Z0-9\&\.\/\?\:@\-_=#])*'
        finalmatches = []
        # --> For URLs without URL encoding characters:
        matches = re.finditer(r'((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:\~@\-_=#]+' + imgsuffix + '', text)
        for match in matches:
            finalmatches.append(match.group())
        #print('URLNOENCODEMATCHES:')
        #for match in matches: print(match)
        # --> For URLs - with - URL encoding characters:
        matches = re.finditer(r'((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\\%:\~@\-_=#]+' + imgsuffix + '', text)
        for match in matches:
            finalmatches.append(match.group())
        #print('URLNOENCODEMATCHES:')
        #for match in matches: print(match)
        #print('FINALMATCHES')
        #for match in finalmatches: print(match)
        finalmatches = list(set(finalmatches))
        return { i : finalmatches[i] for i in range(0, len(finalmatches)) }
    except:
        print('Error grabbing urls!')
        return []
    
# *** --- For converting relative URLs to absolute URLs --- *** #
def reltoabs(relurl, baseurl):
    pass
      
# --> First, check if the database should be reset:

#if bool(os.environ['MORPH_RESET_DB']):
#    if scraperwiki.sql.select('* from data'):
#        scraperwiki.sql.execute('DELETE FROM data')

#from pathlib import Path
#print("File      Path:", Path(__file__).absolute())
#print("Directory Path:", Path().absolute())

#import os
#os.chmod('/usr/local/bin/chromedriver', 755)

#optionuls = webdriver.ChromeOptions()
#optionuls.add_argument('--headless')
#optionuls.add_argument('--disable-dev-shm-usage')
#optionuls.add_argument('--no-sandbox')
#browsur = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver',options=optionuls, service_args=["--verbose"])
#browsur.set_window_size(1920, 1080)
#browsur.get('https://www.nonspecificwebsite.com')

# --> Connect to Wordpress Site via REST API and get all the proper URLs to be scraped!

wp_username = os.environ['MORPH_WP_USERNAME']
wp_password = os.environ['MORPH_WP_PASSWORD']
wp_connectwp_url = os.environ['MORPH_WP_CONNECT_URL']
wp_connectwp_url_2 = os.environ['MORPH_WP_CONNECT_URL_2']
wp_connectwp_url_3 = os.environ['MORPH_WP_CONNECT_URL_3']
wp_connectwp_url_4 = os.environ['MORPH_WP_CONNECT_URL_4']
wp_connectwp_url_5 = os.environ['MORPH_WP_CONNECT_URL_5']
wp_connectwp_url_6 = os.environ['MORPH_WP_CONNECT_URL_6']

encodestring = wp_username + ':' + wp_password;
#token = base64.standard_b64encode(wp_username + ':' + wp_password)
token = base64.b64encode(encodestring.encode())
headers = {'Authorization': 'Basic ' + token.decode('ascii')}

offset = int(os.environ['MORPH_START_OFFSET'])
limit = 25

#r = requests.get(wp_connectwp_url, headers=headers)
r = requests.get(wp_connectwp_url + str(offset) + '/' + str(limit) + '/', headers=headers)
#jsonprods = r.json()
jsonprods = json.loads(r.content)

r = requests.get(wp_connectwp_url_2, headers=headers)
jsonwebsites = json.loads(r.content)

r = requests.get(wp_connectwp_url_3, headers=headers)
jsonprodattr = json.loads(r.content)

r = requests.get(wp_connectwp_url_4, headers=headers)
jsoncatsizetypemaps = json.loads(r.content)

r = requests.get(wp_connectwp_url_5, headers=headers)
jsoncatmaps = json.loads(r.content)

r = requests.get(wp_connectwp_url_6, headers=headers)
jsonsizemaps = json.loads(r.content)

# --> Get the proxy information and related modules!

###wonpr_token = os.environ['MORPH_WONPR_API_TOKEN']
###wonpr_url = os.environ['MORPH_WONPR_CONNECT_URL']
###wonpr_secret_key = os.environ['MORPH_WONPR_SECRET_KEY']
###wonpr_user = os.environ['MORPH_WONPR_USERNAME']
###wonpr_pass = os.environ['MORPH_WONPR_PASSWORD']
###
###encodestring2 = wonpr_token + ':'
###token2 = base64.b64encode(encodestring2.encode())
###wonpr_headers = {'Authorization': 'Basic ' + token2.decode('ascii')}
###
###r = requests.get(wonpr_url, headers=wonpr_headers)
###jsonproxies = json.loads(r.content)
###finalproxies = []

#print(jsonproxies)

###for proxy in jsonproxies:
###    if proxy['server'] == 'stockholm' or proxy['server'] == 'gothenburg':
###        for ip in proxy['ips']:
###            if ip['status'] == 'ok':
###                finalproxies.append(proxy['hostname'] + ':1100' + str(ip['port_base']))
###                break
###                
###proxies = []
###if finalproxies:
###    randomproxy = random.choice(finalproxies)
###    proxies = {'http': 'http://' + wonpr_user + ':' + wonpr_pass + '@' + randomproxy,
###        'https': 'https://' + wonpr_user + ':' + wonpr_pass + '@' + randomproxy,
###        'no_proxy': 'localhost,127.0.0.1'}
