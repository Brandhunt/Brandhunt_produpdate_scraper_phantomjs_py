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

# --> Decode and handle these URLs!

#arraus = []
totalscrapedcount = 0

while jsonprods:
    for website in jsonwebsites:
        # Should we ignore the current website? #
        if website['ignorethisone'] == '1':
            continue
        # Check if there are any initial values to take care of! #
        override_timeout = ''
        altimggrab = ''
        skip_from_img_url = ''
        translate_pa_category_html = '' 
        orig_prodmisc = ''
        if website['productmisc'] != '':
            orig_prodmisc = website['productmisc']
            intro_output = re.search(r'({translate_pa_category_html}(.*?))\{', website['productmisc'])
            if intro_output is not None and len(intro_output.group(1)) > 0:
                translate_pa_category_html = intro_output.group(2)
                website['productmisc'] = re.sub(r'({translate_pa_category_html}.*?(?=\{))', '', website['productmisc'])
            intro_output = re.search(r'({override_timeout}(.*?))\{', website['productmisc'])
            if intro_output is not None and len(intro_output.group(1)) > 0:
                override_timeout = intro_output.group(2)
                website['productmisc'] = re.sub(r'({override_timeout}.*?(?=\{))', '', website['productmisc'])
            intro_output = re.search(r'({alt_img_grab}(.*?))\{', website['productmisc'])
            if intro_output is not None and len(intro_output.group(1)) > 0:
                altimggrab = '1'
                website['productmisc'] = re.sub(r'({alt_img_grab}.*?(?=\{))', '', website['productmisc'])
            intro_output = re.search(r'({alt_img_grab_2}(.*?))\{', website['productmisc'])
            if intro_output is not None and len(intro_output.group(1)) > 0:
                altimggrab = '2'
                website['productmisc'] = re.sub(r'({alt_img_grab_2}.*?(?=\{))', '', website['productmisc'])
            intro_output = re.search(r'({skip_from_img_url}(.*?))\{', website['productmisc'])
            if intro_output is not None and len(intro_output.group(1)) > 0:
                skip_from_img_url = intro_output.group(2)
                website['productmisc'] = re.sub(r'({skip_from_img_url}.*?(?=\{))', '', website['productmisc'])
        # Check each product - See if any of them belong to the current website! #
        for product in jsonprods:
            if website['domain'] == product['domain']:
                # --- First, get the HTML for each domain part --- #
                if website['scrapetype'] == 'phantomjs_morph_io':
                    try:
                        #with Browser("phantomjs") as browser:
                        ##chrome_options = Options()
                        #chrome_options.add_argument("--headless")
                        #chrome_options.add_argument("--disable-gpu")
                        ##chrome_options.add_argument('--no-sandbox')
                        ##chrome_options.add_argument('--disable-extensions')
                        #chrome_options.binary_location = '/usr/bin/google-chrome'
                        #browser = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', chrome_options=chrome_options)
                        #with Browser('chrome', headless=True, options=chrome_options) as browser:
                        optionals = Options()
                        #optionals.add_argument('--no-proxy-server')
                        #optionals.add_argument("--proxy-server='direct://'")
                        #optionals.add_argument("--proxy-bypass-list=*")
                        optionals.add_argument('--disable-dev-shm-usage')
                        optionals.add_argument('--disable-extensions')
                        optionals.add_argument('--no-sandbox')
                        optionals.add_argument("--headless")
                        ###optionals.add_argument("--proxy-server=" + proxies['https'] + "")
                        #optionals.add_argument('--lang=en_US') 
                        #optionals.add_argument('--lang=sv')
                        optionals.add_experimental_option('prefs', {'intl.accept_languages': 'sv',
                                                                   'profile.default_content_setting_values.geolocation': 1,
                                                                   "profile.default_content_settings.geolocation": 1})
                        ###optionals_wire = { 'proxy': proxies }
                        #optionals.add_argument('--disable-gpu')
                        #optionals.add_argument('--ignore-certificate-errors')
                        #optionals.add_argument("--start-maximized") 
                        #optionals.add_argument("disable-infobars") 
                        html_source = ''
                        root = ''
                        #with Browser('chrome', headless=True, options=optionals, service_args=['--ignore-ssl-errors=true', '--ssl-protocol=any']) as browser:
                        #with Browser('chrome', headless=True, options=optionals) as browser:
                        ###with webdriver.Chrome(options=optionals, seleniumwire_options=optionals_wire) as driver:
                        with webdriver.Chrome(options=optionals) as driver:
                            #browser.driver.close()
                            #browser.driver = webdriver.Chrome(options=optionals, seleniumwire_options=optionals_wire)
                            #browser = webdriver.Chrome(options=optionals, service_args=["--verbose"])
                            driver.set_page_load_timeout(300)
                            driver.set_window_size(1920, 1080)
                            params = {"latitude": 59.3521,
                              "longitude": 18.0041,
                              "accuracy": 100}
                            response = driver.execute_cdp_cmd("Page.setGeolocationOverride", params)
                            # submit the search form...
                            ##browser.fill("q", "parliament")
                            ##button = browser.find_by_css("button[type='submit']")
                            ##button.click()
                            # Scrape the data you like...
                            ##links = browser.find_by_css(".search-results .list-group-item")
                            ##for link in links:
                            ##    print link['href']
                            # >>> VISIT THE PAGE THROUGH BROWSER <<< #
                            try:
                                #browser.driver.implicitly_wait(30) # seconds
                                driver.get(product['url'])
                                #myDynamicElement = browser.driver.find_element_by_id("attribute135")
                                #time.sleep(25)
                                if override_timeout != '':
                                    time.sleep(int(override_timeout))
                                else:
                                    time.sleep(2)
                                #browser.driver.refresh()
                                html_source = driver.page_source
                                #html_source = browser.driver.page_source
                                #html_source = browser.driver.execute_script('return document.documentElement.outerHTML')
                                driver.quit()
                                #browser.get(product['url'])
                                #print("HTML:")
                                #print(html_source)
                                #print(browser.driver.page_source)
                            except HTTPError as err:
                                if err.code == 302:
                                    try:
                                        url_headers = {'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',\
                                        'User-Agent':'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36',\
                                                  'Accept-Encoding':'gzip, deflate',\
                                                  'Accept-Language':'en-US,en;q=0.8'}
                                        url_session = requests.session()
                                        response = url_session.get(url=product['url'], headers=url_headers)
                                        html = response.content
                                    except:
                                        print(traceback.format_exc())
                                elif err.code == 404:
                                    notfound = True
                                    removeon404 = False
                                    if website['productmisc']:
                                        if website['productmisc'].find('allow_remove_on_404'):
                                                removeon404 = True
                                    try:
                                        scraperwiki.sqlite.save(unique_keys=['productid'],\
                                                    data={'productid': product['productid'],\
                                                          'url': product['url'],\
                                                          'domain': product['domain'],\
                                                          'price': '',\
                                                          'salesprice': '',\
                                                          'domainmisc':  '',\
                                                          'prodlogurls': '',\
                                                          'prodlogurl': '',\
                                                          'finalimgurls': '',\
                                                          'validimgurls': '',\
                                                          'imgurls': '',\
                                                          'notfound': notfound,\
                                                          'notavailable': True,\
                                                          'removeon404': removeon404,\
                                                          'soldoutfix': '',\
                                                          'soldouthtmlfix': '',\
                                                          'catstoaddresult': '',\
                                                          'attributes': '',\
                                                          'sizetypemapsqls': ''})
                                        totalscrapedcount = totalscrapedcount + 1
                                        continue
                                    except:
                                        print(traceback.format_exc())
                                        continue
                                else:
                                    raise
                            except WebDriverException:
                                print('Chrome not reachable - The product will be rescraped again!')
                                jsonprods.append(product)
                                time.sleep(2)
                                continue
                            except:
                                #print("Error when scraping URL for product ID " + product['productid'] + ": " + str(sys.exc_info()[0]) + " occured!")
                                print(traceback.format_exc())
                        # # # # # print("Currently scraping product with ID " + str(product['productid'])) # # # # #
                        # >>> GET THE HTML ROOT <<< #
                        root = lxml.html.fromstring(html_source)
                        # >>> GET THE PRICE <<< #
                        price_elements = ''
                        price = ''
                        #print(website['priceselector'])
                        try:
                            website['priceselector'] = website['priceselector'].encode().decode("unicode-escape")
                            #print(website['priceselector'])
                            if website['priceselector'].find('[multiple],') != -1:
                                website['priceselector'].replace('[multiple],', '')
                                #price_elements = browser.find_by_css(website['priceselector'])
                                price_elements = root.cssselect(website['priceselector'])
                                for el in price_elements:
                                    if el is None:
                                        continue
                                    price = price + el.text + ' '
                                if price != '':
                                    price = re.sub(r'([^a-zA-Z]\w+\%+)', '', price)
                            else:
                                #price_elements = browser.find_by_css(website['priceselector'])
                                price_elements = root.cssselect(website['priceselector'])
                                if price_elements:
                                    for price_el in price_elements:
                                        if price_el.text is not None:
                                            if any(char.isdigit() for char in price_el.text):
                                                price = price_el.text
                                                price = re.sub(r'([^a-zA-Z]\w+\%+)', '', price)
                                                break
                                            else:
                                                price = '-1'
                                else:
                                    price = '-1'
                            if website['pricedelimitertoignore']:
                                if website['pricedelimitertoignore'].strip().find(' ') != -1:
                                    sepdelimiters = website['pricedelimitertoignore'].strip().split(' ')
                                    for delim in sepdelimiters:
                                        price = re.sub('\\' + delim.strip() + '', '', price)
                                else:
                                    price = re.sub('\\' + website['pricedelimitertoignore'].strip() + '', '', price)    
                            if website['currencysymbol']:
                                #print('PRICEBEFORECONVERSION:' + price)
                                #print('PRICE ELEMENTS:')
                                #for p in price_elements: print p
                                price = converttocorrectprice(price, website['currencysymbol'])
                            else:
                                price = price.replace(r'[^0-9,.]', '')
                                price = getmoneyfromtext(price)
                            #print('FINALPRICE:' + price)
                        except:
                            #print("Error when scraping price for product ID " + product['productid'] + ": " + sys.exc_info()[0] + " occured!")
                            print(traceback.format_exc())
                        # >>> GET THE SALES PRICE <<< #
                        salesprice_elements = ''
                        salesprice = ''
                        if website['salespriceselector']:
                            try:
                                website['salespriceselector'] = website['salespriceselector'].encode().decode("unicode-escape")
                                #salesprice_elements = browser.find_by_css(website['salespriceselector'])
                                salesprice_elements = root.cssselect(website['salespriceselector'])
                                if salesprice_elements:
                                    if any(char.isdigit() for char in salesprice_elements[0].text):
                                        salesprice = salesprice_elements[0].text
                                        salesprice = re.sub(r'([^a-zA-Z]\w+\%+)', '', salesprice)
                                    else:
                                        salesprice = '-1'
                                else:
                                    salesprice = '-1'
                                if website['pricedelimitertoignore']:
                                    if website['pricedelimitertoignore'].strip().find(' ') != -1:
                                        sepdelimiters = website['pricedelimitertoignore'].strip().split(' ')
                                        for delim in sepdelimiters:
                                            salesprice = re.sub('\\' + delim.strip() + '', '', salesprice)
                                    else:
                                        salesprice = re.sub('\\' + website['pricedelimitertoignore'].strip() + '', '', salesprice)    

                                if website['currencysymbol']:
                                    salesprice = converttocorrectprice(salesprice, website['currencysymbol'])
                                else:
                                    salesprice = salesprice.replace(r'[^0-9,.]', '')
                                    salesprice = getmoneyfromtext(salesprice)
                                #print('FINALSALESPRICE:' + salesprice)
                            except:
                                #print("Error when scraping sales price for product ID " + product['productid'] + ": " + sys.exc_info()[0] + " occured!")
                                print(traceback.format_exc())
                        # >>> GET THE DOMAIN MISC. ELEMENTS <<< #
                        domainmisc_array = ''
                        if website['domainmisc']:
                            try:
                                domainmisc_array = re.split('{|}', website['domainmisc'])
                                for i in range(1, len(domainmisc_array), 2):
                                    domainmisc_array[i] = root.cssselect(domainmisc_array[i])
                                    #domainmisc_array[i] = browser.find_by_css(domainmisc_array[i])
                                #print('DOMAINMISC:')
                                #for d in domainmisc_array: print d
                            except:
                                #print("Error when scraping misc. domain information for product ID " + product['productid'] + ": " + sys.exc_info()[0] + " occured!")
                                print(traceback.format_exc())
                        # >>> GET THE PRODUCT LOGO URL(S) - IF SUCH EXISTS <<< #
                        #prodlog_image_urls = ''
                        #prodlog_image_elements = ''
                        prodlog_image_urls = ''
                        productlogourl = ''
                        #productlogo = ''
                        if website['productlogoselector']:
                            try:
                                website['productlogoselector'] = website['productlogoselector'].encode().decode("unicode-escape")
                                #prodlog_image_elements = browser.find_by_css(website['productlogoselector'])
                                prodlog_image_elements = root.cssselect(website['productlogoselector'])
                                if prodlog_image_elements:
                                    for i in range(len(prodlog_image_elements)):
                                        #print('HUPP: ' + prodlog_image_elements[i])
                                        prodlog_image_elements[i] = str(etree.tostring(prodlog_image_elements[i]))
                                        #prodlog_image_elements[i] = prodlog_image_elements[i]._element.get_attribute('outerHTML')
                                    image_dom = ','.join(prodlog_image_elements)
                                    #print('IMAGEDOM: ' + image_dom)
                                    if altimggrab == '1':
                                        output = re.search(r'image\=\"(.*?)\"', image_dom)
                                        if len(output.group(1)) > 0:
                                            prodlog_image_urls = { 0 : output.group(1) }
                                    elif altimggrab == '2':
                                        output = re.search(r'src\=\"(.*?)\"', image_dom)
                                        if len(output.group(1)) > 0:
                                            prodlog_image_urls = { 0 : output.group(1) }
                                    else:
                                        prodlog_image_urls = graburls(str(image_dom), True)
                                    if len(prodlog_image_urls) > 0:
                                        for imagekey, imageval in prodlog_image_urls.copy().items():
                                            #print('OLD: ' + imageval)
                                            newimageval = urljoin(product['url'], imageval)
                                            #print('NEW: ' + newimageval)
                                            if imageval != newimageval:
                                                prodlog_image_urls[imagekey] = newimageval
                                                imageval = newimageval
                                            if imageval.find('//') == -1:
                                                del prodlog_image_urls[imagekey]
                                                continue
                                            if imageval[0:2] == '//':
                                                imageval = 'https:' + imageval
                                                prodlog_image_urls[imagekey] = imageval
                                    #print('HEPP')
                                    #for prod in prodlog_image_urls: print(prod)
                                    productlogourl = prodlog_image_urls[0]   
                                else:
                                    print("No product logo URLs could be found for product ID " + product['productid'] + "!")
                                #print('PRODUCTLOGOS:')
                                #for p in prodlog_image_urls: print(p)
                                #print('PRODUCTLOGOURL:' + productlogourl)
                            except:
                                #print("Error when scraping product logo images for product ID " + product['productid'] + ": " + sys.exc_info()[0] + " occured!")
                                print(traceback.format_exc())
                        # >>> GET THE IMAGE URL(S) <<< #
                        image_urls = ''
                        image_elements = ''
                        image_urls_valid = ''
                        images = ''
                        if website['imageselector'] and len(website['imageselector']):
                            try:
                                website['imageselector'] = website['imageselector'].encode().decode("unicode-escape")
                                #image_urls = ''
                                #image_elements = browser.find_by_css(website['imageselector'])
                                image_elements = root.cssselect(website['imageselector'])
                                if image_elements:
                                    for i in range(len(image_elements)):
                                        image_elements[i] = str(etree.tostring(image_elements[i]))
                                        #image_elements[i] = image_elements[i]._element.get_attribute('outerHTML')
                                    image_dom = ','.join(image_elements)
                                    #print('IMAGE DOM: ' + image_dom)
                                    if altimggrab == '1':
                                        output = re.finditer(r'image\=\"(.*?)\"', image_dom)
                                        array_output = []
                                        for output_el in output:
                                            array_output.append(output_el.group(1))
                                        if len(array_output) > 0:
                                            image_urls = { i : array_output[i] for i in range(0, len(array_output)) }
                                    elif altimggrab == '2':
                                        output = re.search(r'src\=\"(.*?)\"', image_dom)
                                        if len(output.group(1)) > 0:
                                            image_urls = { 0 : output.group(1) }
                                    else:
                                        image_urls = graburls(str(image_dom), True)
                                    #print('PRE-IMAGE URLS: ')
                                    #for img in image_urls: print(img)
                                if len(image_urls) > 0:
                                    for imagekey, imageval in image_urls.copy().items():
                                        newimageval = urljoin(product['url'], imageval)
                                        if imageval != newimageval:
                                            image_urls[imagekey] = newimageval
                                            imageval = newimageval
                                        if imageval.find('//') == -1 or imageval.find('blank.') != -1:
                                            del image_urls[imagekey]
                                            continue
                                        if imageval[0:2] == '//':
                                            imageval = 'https:' + imageval
                                            image_urls[imagekey] = imageval
                                        if skip_from_img_url != '':
                                            #print('TO SKIP:')
                                            #print(':::' + skip_from_img_url + ':::')
                                            #print(image_urls[imagekey])
                                            image_urls[imagekey] = image_urls[imagekey].replace(skip_from_img_url, '')
                                            #print(image_urls[imagekey])
                                    image_urls_valid = sorted(list(image_urls.values()))
                                #print('IMAGE ELEMENTS:')
                                #for img in image_elements: print img
                                #print('IMAGE URLS:')
                                #for img in image_urls: print img
                                #print('VALID IMAGES:')
                                #for img in image_urls_valid: print img
                            except:
                                #print("Error when scraping images for product ID " + product['productid'] + ": " + sys.exc_info()[0] + " occured!")
                                print(traceback.format_exc())
                        # >>> GET THE PRODUCT MISC. ELEMENTS <<< #
                        productmisc_array = re.split('{|}', website['productmisc'])
                        #print('PRODUCTMISCARRAY BEFORE:')
                        #for p in productmisc_array: print p
                        # --> Define containers for product attributes
                        product_brand = ''
                        product_colors = ''
                        product_sex = ''
                        product_sizes = ''
                        product_sizetypes = ''
                        product_sizetypemiscs = ''
                        product_categories = ''
                        # --> Define values that will be saved to database once done:
                        sizetypemisc = ''
                        preexistingcurrency = ''
                        notfound = False
                        notavailable = False
                        shouldremoveonnotfound = False
                        soldoutupdatemeta = False
                        soldouthtmlupdatemeta = False
                        catstoaddresult = ''
                        attributes_to_store = ''
                        insert_sizetosizetype = ''
                        remove_sizetosizetype = ''
                        insert_sizetosizetypemisc = ''
                        remove_sizetosizetypemisc = ''
                        skip_exist_attr = [0, 0, 0, 0, 0, 0, 0] # <==> [brand, color, sex, size, s-type, s-t-misc, categories]
                        skip_exist_attr_prodtitle = [0, 0, 0, 0] # <==> [brand, color, sex, categories]
                        no_whitespace_htmlregex = False
                        no_whitespace_prodtitleregex = False
                        # --> Define misc. storage variables
                        domain_name = ''
                        # --> Get 'em!
                        if website['productmisc']:
                            try:
                                for i in range(2, len(productmisc_array), 2):
                                    #print(productmisc_array[(i-1)])
                                    #print(productmisc_array[i])
                                    # --- Set product as 'Not Available' if the product has been found but the price is not available? --- #
                                    if productmisc_array[(i-1)] == 'allow_not_available':
                                        if price == '1':
                                            notavailable = True
                                    # --- No leading/trailing whitespaces when using regex while searching prod. title for attributes? --- #
                                    if productmisc_array[(i-1)] == 'no_whitespace_prodtitleregex':
                                        no_whitespace_prodtitleregex = True
                                    # --- No leading/trailing whitespaces when using regex while searching pure HTML for attributes? --- #
                                    if productmisc_array[(i-1)] == 'no_whitespace_htmlregex':
                                        no_whitespace_htmlregex = True
                                    # --- Are the sizes belonging to the current product of a a specific misc. size type? --- #
                                    if productmisc_array[(i-1)] == 'sizetypemisc':
                                        sizetypemisc = productmisc_array[i]
                                    # --- Should we skip any already existing product attributes when scraping the product? --- #
                                    if productmisc_array[(i-1)] == 'skip_exist_attr':
                                        if productmisc_array[i] != 'true':
                                            skip_exist_attr = [ int(skipval) for skipval in productmisc_array[i].strip().split(',') ]
                                            productmisc_array[i] = 'true'
                                    # --- Should we skip any already existing product attributes when scraping the product? --- #
                                    if productmisc_array[(i-1)] == 'skip_exist_attr_prodtitle':
                                        if productmisc_array[i] != 'true':
                                            skip_exist_attr_prodtitle = [ int(skipval) for skipval in productmisc_array[i].strip().split(',') ]
                                            productmisc_array[i] = 'true'
                                    # --- Should we skip any sizes that correspond with other page elements on a certain condition? --- #
                                    # !!! IMPORTANT --- PUT THIS AFTER ALL STANDARD SIZES HAVE BEEN IMPORTED FROM PRODUCTMISC STRING! --- IMPORTANT !!! #
                                    if productmisc_array[(i-1)] == 'skip_pa_size_on_corrsp':
                                        if product_sizes != '':
                                            corrsp_elements = productmisc_array[i].split(',')
                                            corrsp_elements[0] = root.cssselect(corrsp_elements[0].encode().decode("unicode-escape"))
                                            corrsp_elements[1] = corrsp_elements[1].strip().split('|')
                                            if corrsp_elements[1][0] == 'bool_text':
                                                count = 0
                                                for el in corrsp_elements[0]:
                                                    if el.text is not None:
                                                        if el.text == corrsp_elements[1][1]:
                                                            del product_sizes[count]
                                                            continue
                                                    count += 1
                                        productmisc_array[i] = 'true'
                                    # --- Are there any pre-existing currencies to apply to the price(s)? --- #
                                    if productmisc_array[(i-1)] == 'pre_existing_currency':
                                        preexistingcurrency = productmisc_array[i]
                                        newprice = ''
                                        newprice = price + productmisc_array[i].strip()
                                        if website['currencysymbol']:
                                            newprice.upper()
                                            newprice = converttocorrectprice(newprice, website['currencysymbol'])
                                        else:
                                            newprice = newprice.replace(r'[^0-9,.]', '')
                                            newprice = getmoneyfromtext(newprice)
                                        price = newprice
                                        if salesprice != '':
                                            newprice = ''
                                            newprice = salesprice + productmisc_array[i].strip()
                                            if website['currencysymbol']:
                                                newprice.upper()
                                                newprice = converttocorrectprice(newprice, website['currencysymbol'])
                                            else:
                                                newprice = newprice.replace(r'[^0-9,.]', '')
                                                newprice = getmoneyfromtext(newprice)
                                            salesprice = newprice
                                    # --- Should the product skip any URLs(Product logo and normal IMGs) containing any specific string(s)? --- #
                                    if productmisc_array[(i-1)] == 'skip_img_containing':
                                        if image_urls_valid != '':
                                            count = 0
                                            for e in range(0, len(image_urls_valid), 1):
                                                if image_urls_valid[(e+count)].find(productmisc_array[i].strip()) != -1:
                                                    del image_urls_valid[e+count]
                                                    count-=1
                                                images = ','.join(image_urls_valid)
                                        if prodlog_image_urls != '':
                                            for imagekey, imageval in prodlog_image_urls.copy().items():
                                                if imageval.find(productmisc_array[i].strip()) != -1:
                                                    del prodlog_image_urls[imagekey]
                                            productlogourl = prodlog_image_urls[0]       
                                    # --- Should we remove the product on 404 Error? --- #
                                    if productmisc_array[(i-1)] == 'allow_remove_on_404':
                                        shouldremoveonnotfound = True
                                    # --- Use custom domain name(In case any brands doesn't exist for current product) --- #
                                    if productmisc_array[(i-1)] == 'domain_name':
                                        brand_array = []
                                        if productmisc_array[i] != '':
                                            brand_termus = productmisc_array[i].strip()
                                            domain_name = brand_termus
                                            clean_brand = slugify(brand_termus.strip())
                                            term = doesprodattrexist(jsonprodattr['pa_brand'], brand_termus, 'pa_brand')
                                             #TUPPLE STRUCTURE: (Term(ID/NAME/SLUG), newtermTrue_existingtermFalse)
                                            if term:
                                                brand_array.append((term, False))
                                            else:
                                                term = {'term_id':-1, 'name':brand_termus, 'slug':clean_brand, 'taxonomy':'pa_brand'}
                                                brand_array.append((term, True))
                                            product_brand = brand_array
                                            productmisc_array[i] = '.somethingelse'
                                    # --- Should the product apply a specific category automatically? --- #
                                    if productmisc_array[(i-1)] == 'add_category':
                                       cats_to_add = ','.split(productmisc_array[i])
                                       cat_result = []
                                       for cat in cats_to_add:
                                          clean_cat = slugify(cat.strip())
                                          term = doesprodattrexist(jsonprodattr['product_cat'], cat, 'product_cat')
                                          #TUPPLE STRUCTURE: (Term(ID/NAME/SLUG), newtermTrue_existingtermFalse, resultcats)
                                          if term:
                                             if not list(filter(lambda x: x[0]['term_id'] == term['term_id'], cat_result)):
                                                 cat_result.append((term, False))
                                                 cat_parents = term['ancestors']
                                                 for parent_id in cat_parents:
                                                     parent = doesprodattrexist(jsonprodattr['product_cat'], parent_id, 'product_cat')
                                                     if not list(filter(lambda x: x[0]['term_id'] == parent['term_id'], cat_result)):
                                                        cat_result.append((parent, False))
                                          else:
                                              term = {'term_id':-1, 'name':cat, 'slug':clean_cat, 'taxonomy':'product_cat'}
                                              cat_result.append((term, True))
                                       product_categories = cat_result
                                    # --- Should the product apply the male/female attribute automatically? --- #
                                    # --- !!! IMPORTANT --> IF THIS SHOULD OVERRIDE OTHER SEX ATTR. IMPORTS, !!! --- #
                                    # --- !!! THEN PUT THIS LAST IN ORDER IN PRODUCTMISC. TEXT FIELD BEFORE SCRAPING !!! --- #
                                    if product_sex == '':
                                        if productmisc_array[(i-1)] == 'is_male':
                                            product_sex = [(doesprodattrexist(jsonprodattr['pa_sex'], 'Male', 'pa_sex'), False)]
                                        elif productmisc_array[(i-1)] == 'is_female':
                                            product_sex = [(doesprodattrexist(jsonprodattr['pa_sex'], 'Female', 'pa_sex'), False)]
                                        #print('SEX VALUES:')
                                        #print(i)
                                        #for sex in product_sex: print(sex)
                                    # --> Attempt scraping of product misc. elements:
                                    prodmisc_backup = productmisc_array[i].strip().encode().decode("unicode-escape")
                                    #productmisc_array[i] = browser.find_by_css(productmisc_array[i].encode().decode("unicode-escape"))
                                    productmisc_array[i] = root.cssselect(productmisc_array[i].encode().decode("unicode-escape"))
                                    if productmisc_array[i]:
                                        # --- Has the product got any special sale price applied? --- #
                                        if productmisc_array[(i-1)] == 'before_sale_price':
                                            if len(productmisc_array[i]) > 0:
                                                newprice = productmisc_array[i][0].text
                                                if website['currencysymbol']:
                                                    newprice.upper()
                                                    if website['pricedelimitertoignore']:
                                                        if website['pricedelimitertoignore'].strip().find(' ') != -1:
                                                            sepdelimiters = website['pricedelimitertoignore'].strip().split(' ')
                                                            for delim in sepdelimiters:
                                                                newprice = re.sub('\\' + delim.strip() + '', '', newprice)
                                                        else:
                                                            newprice = re.sub('\\' + website['pricedelimitertoignore'].strip() + '', '', newprice) 
                                                    newprice = converttocorrectprice(newprice, website['currencysymbol'])
                                                else:
                                                    newprice = newprice.replace(r'[^0-9,.]', '')
                                                    newprice = getmoneyfromtext(newprice)   
                                                salesprice = price
                                                price = newprice
                                        # --- Get sex attributes from current scrape --- #
                                        if productmisc_array[(i-1)] == 'pa_sex':
                                            if len(productmisc_array[i]) > 0:
                                                sex_array = []
                                                for sex_termus in productmisc_array[i]:
                                                    sex_termus = sex_termus.text
                                                    check_sex = sex_termus.lower()
                                                    if check_sex == 'men' or check_sex == 'man':
                                                        sex_termus = 'male'
                                                    elif check_sex == 'women' or check_sex == 'woman':
                                                        sex_termus = 'female'
                                                    clean_sex = sex_termus.strip()
                                                    term = doesprodattrexist(jsonprodattr['pa_sex'], sex_termus, 'pa_sex')
                                                    #TUPPLE STRUCTURE: (Term(ID/NAME/SLUG), newtermTrue_existingtermFalse)
                                                    if term:
                                                        sex_array.append((term, False))
                                                    else:
                                                        term = {'term_id':-1, 'name':sex_termus, 'slug':clean_sex, 'taxonomy':'pa_sex'}
                                                        sex_array.append((term, True))
                                                product_sex = sex_array
                                        # --- Get brand attribute(s) from current scrape --- #
                                        if productmisc_array[(i-1)] == 'pa_brand':
                                            brand_array = []
                                            if len(productmisc_array[i]) > 0 and productmisc_array[i][0] is not None:
                                                brand_termus = productmisc_array[i][0].text
                                                if brand_termus is not None:
                                                    clean_brand = slugify(brand_termus.strip())
                                                    term = doesprodattrexist(jsonprodattr['pa_brand'], brand_termus, 'pa_brand')
                                                    # TUPPLE STRUCTURE: (Term(ID/NAME/SLUG), newtermTrue_existingtermFalse)
                                                    if term:
                                                        brand_array.append((term, False))
                                                    else:
                                                        term = {'term_id':-1, 'name':brand_termus, 'slug':clean_brand, 'taxonomy':'pa_brand'}
                                                        brand_array.append((term, True))
                                                    product_brand = brand_array
                                        # --- Get size attributes from current scrape --- #
                                        if productmisc_array[(i-1)] == 'pa_size':
                                            if len(productmisc_array[i]) > 0:
                                                #PRINT('SIZES, PRODUCTMISC_SCRAPES:')
                                                #for size in productmisc_array[i]: print(size)
                                                size_array = []
                                                for size_termus in productmisc_array[i]:
                                                    #print(etree.tostring(size_termus))
                                                    size_text = size_termus.text
                                                    #print(size_termus)
                                                    #print(size_termus.text)
                                                    #print("".join(size_termus.itertext()))
                                                    if size_text is None:
                                                        if size_termus.tail is None:
                                                            size_termus = "".join(size_termus.itertext())
                                                        else:
                                                            size_termus = size_termus.tail
                                                    else:
                                                        size_termus = size_text
                                                    output = re.search(r'\(.*Only.*\)|\(.*Out.*\)|\(.*In.*\)|\(.*Lager.*\)', size_termus, flags=re.IGNORECASE)
                                                    output2 = re.search(r'.*Bevaka.*', size_termus, flags=re.IGNORECASE)
                                                    output3 = re.search(r'.*Stock.*', size_termus, flags=re.IGNORECASE)
                                                    output4 = re.search(r'.*Size\s+\d+.*', size_termus, flags=re.IGNORECASE)
                                                    output5 = re.search(r'.*Choose.*', size_termus, flags=re.IGNORECASE)
                                                    output6 = re.search(r'.*Empty.*', size_termus, flags=re.IGNORECASE)
                                                    output7 = re.search(r'.*Select.*', size_termus, flags=re.IGNORECASE)
                                                    output8 = re.search(r'.*storlek.*', size_termus, flags=re.IGNORECASE)
                                                    if output is not None:
                                                        size_termus = re.sub(r'\(.*\)', '', size_termus, flags=re.IGNORECASE)
                                                    elif output2 is not None:
                                                        size_termus = re.sub(r'\s+-\s+Bevaka.*', '', size_termus, flags=re.IGNORECASE)
                                                    elif output3 is not None:
                                                        size_termus = re.sub(r'\s+-\s+.*Stock.*', '', size_termus, flags=re.IGNORECASE)
                                                    elif output4 is not None:
                                                        size_termus = re.sub(r'.*Size\s+', '', size_termus, flags=re.IGNORECASE)
                                                    elif output5 is not None:
                                                        size_termus = re.sub(r'.*Choose.*', '', size_termus, flags=re.IGNORECASE)
                                                    elif output6 is not None:
                                                        size_termus = re.sub(r'.*Empty.*', '', size_termus, flags=re.IGNORECASE)
                                                    elif output7 is not None:
                                                        size_termus = re.sub(r'.*Select.*', '', size_termus, flags=re.IGNORECASE)
                                                    elif output8 is not None:
                                                        size_termus = re.sub(r'.*storlek.*', '', size_termus, flags=re.IGNORECASE)
                                                    size_termus = size_termus.replace(' ', '').replace('\n', '')
                                                    clean_size = slugify(size_termus.strip())
                                                    term = doesprodattrexist(jsonprodattr['pa_size'], size_termus, 'pa_size')
                                                    if term:
                                                        size_array.append((term, False))
                                                    else:
                                                        term = {'term_id':-1, 'name':size_termus, 'slug':clean_size, 'taxonomy':'pa_size'}
                                                        size_array.append((term, True))
                                                product_sizes = size_array
                                        # --- Get color attributes from current scrape --- #
                                        if productmisc_array[(i-1)] == 'pa_color':
                                            if len(productmisc_array[i]) > 0:
                                                color_array = []
                                                for color_termus in productmisc_array[i]:
                                                    color_termus = color_termus.text
                                                    if color_termus is not None:
                                                        clean_color = slugify(color_termus.strip())
                                                        term = doesprodattrexist(jsonprodattr['pa_color'], color_termus, 'pa_color')
                                                        if term:
                                                            color_array.append((term, False))
                                                        else:
                                                            term = {'term_id':-1, 'name':color_termus, 'slug':clean_color, 'taxonomy':'pa_color'}
                                                            color_array.append((term, True))
                                                product_colors = color_array
                                        # --- Get categories from current scrape --- #
                                        if productmisc_array[(i-1)] == 'pa_category':
                                            if len(productmisc_array[i]) > 0:
                                                category_array = []
                                                for cat_termus in productmisc_array[i]:
                                                    cat_termus = cat_termus.text
                                                    clean_cat = slugify(cat_termus.strip())
                                                    term = doesprodattrexist(jsonprodattr['product_cat'], cat_termus, 'product_cat')
                                                    if term:
                                                        if not list(filter(lambda x: x[0]['term_id'] == term['term_id'], category_array)):
                                                            category_array.append((term, False))
                                                            cat_parents = term['ancestors']
                                                            for parent_id in cat_parents:
                                                                parent = doesprodattrexist(jsonprodattr['product_cat'], parent_id, 'product_cat')
                                                                if not list(filter(lambda x: x[0]['term_id'] == parent['term_id'], category_array)):
                                                                    category_array.append((parent, False))
                                                    else:
                                                        term = {'term_id':-1, 'name':cat_termus, 'slug':clean_cat, 'taxonomy':'product_cat'}
                                                        category_array.append((term, True))
                                                if category_array:
                                                    if product_categories != '':
                                                        product_categories = array_merge(product_categories, category_array)
                                                    else:
                                                        product_categories = category_array
                                        # --- Is the product no longer existing - Does the page for it not exist anymore? --- #
                                        if productmisc_array[(i-1)] == 'notfound':
                                            if len(productmisc_array[i]) > 0:
                                                notfound = True
                                        # --- Has the product sold out yet? --- #
                                        if productmisc_array[(i-1)] == 'sold_out':
                                            if len(productmisc_array[i]) > 0:
                                                soldoutupdatemeta = True
                                                price = '0.0 BUCKS'
                                                price = price.replace(r'[^0-9,.]', '')
                                                price = getmoneyfromtext(price)
                                            else:
                                                soldoutupdatemeta = False
                                        # --> Check the HTML if neccessary! Any already existing product attributes found there?
                                        #productmisc_array[i] = lxml.html.tostring(productmisc_array[i])
                                        #productmisc_array[i] = etree.tostring(productmisc_array[i][0])
                                        #selected = browser.find_by_css(prodmisc_backup.strip().encode().decode("unicode-escape"))
                                        selected = root.cssselect(prodmisc_backup.strip().encode().decode("unicode-escape"))
                                        #productmisc_array[i] = selected[0].html
                                        productmisc_array[i] = str(etree.tostring(selected[0]))
                                        # --- Get sex attributes from current scrape --- #
                                        if productmisc_array[(i-1)] == 'pa_sex_html':
                                            sexies = jsonprodattr['pa_sex']
                                            sexies_result = []
                                            for sexterm in sexies:
                                                term_name = sexterm['name']
                                                sex_html = str(productmisc_array[i])
                                                regex = ''
                                                if term_name == 'Male':
                                                    regex = r'\bmale\b|\bmen\b|\bman\b'
                                                elif term_name == 'Female':
                                                    regex = r'\bfemale\b|\bwomen\b|\bwoman\b'
                                                #if sex_html.upper().find(term_name.upper()) != -1:
                                                if re.search(regex, sex_html, flags=re.IGNORECASE):
                                                    term = doesprodattrexist(jsonprodattr['pa_sex'], sexterm['term_id'], 'pa_sex')
                                                    if term:
                                                        sexies_result.append((term, False))
                                            product_sex = sexies_result
                                        # --- Get size attribute(s) from current scrape --- #
                                        if productmisc_array[(i-1)] == 'pa_size_html':
                                            sizies = jsonprodattr['pa_size']
                                            sizies_result = []
                                            for sizeterm in sizies:
                                                term_name = sizeterm['name']
                                                size_html = str(productmisc_array[i])
                                                output = re.search(r'\(.*Only.*\)|\(.*Out.*\)|\(.*In.*\)|\(.*Lager.*\)', size_html, flags=re.IGNORECASE)
                                                output2 = re.search(r'.*Bevaka.*', size_html, flags=re.IGNORECASE)
                                                output3 = re.search(r'.*Stock.*', size_html, flags=re.IGNORECASE)
                                                output4 = re.search(r'.*Size\s+\d+.*', size_html, flags=re.IGNORECASE)
                                                output5 = re.search(r'.*Choose.*', size_html, flags=re.IGNORECASE)
                                                output6 = re.search(r'.*Empty.*', size_html, flags=re.IGNORECASE)
                                                output7 = re.search(r'.*Select.*', size_html, flags=re.IGNORECASE)
                                                output8 = re.search(r'.*storlek.*', size_html, flags=re.IGNORECASE)
                                                if output is not None:
                                                    size_html = re.sub(r'\(.*\)', '', size_html, flags=re.IGNORECASE)
                                                elif output2 is not None:
                                                    size_html = re.sub(r'\s+-\s+Bevaka.*', '', size_html, flags=re.IGNORECASE)
                                                elif output3 is not None:
                                                    size_html = re.sub(r'\s+-\s+.*Stock.*', '', size_html, flags=re.IGNORECASE)
                                                elif output4 is not None:
                                                    size_html = re.sub(r'.*Size\s+', '', size_html, flags=re.IGNORECASE)
                                                elif output5 is not None:
                                                    size_html = re.sub(r'.*Choose.*', '', size_html, flags=re.IGNORECASE)
                                                elif output6 is not None:
                                                    size_html = re.sub(r'.*Empty.*', '', size_html, flags=re.IGNORECASE)
                                                elif output7 is not None:
                                                    size_html = re.sub(r'.*Select.*', '', size_html, flags=re.IGNORECASE)
                                                elif output8 is not None:
                                                    size_html = re.sub(r'.*storlek.*', '', size_html, flags=re.IGNORECASE)
                                                if size_html.upper().find(term_name.upper()) != -1:
                                                    term = doesprodattrexist(jsonprodattr['pa_size'], sizeterm['term_id'], 'pa_size')
                                                    if term:
                                                        sizies_result.append((term, False))
                                            if sizies_result:
                                                if product_sizes == '':
                                                    product_sizes = sizies_result
                                                else:
                                                    product_sizes = array_merge(product_sizes, sizies_result)
                                        # --- Get brand attributes from current scrape --- #
                                        if productmisc_array[(i-1)] == 'pa_brand_html':
                                            brandies = jsonprodattr['pa_brand']
                                            brandies_result = []
                                            for brandterm in brandies:
                                                term_name = brandterm['name']
                                                brand_html = str(productmisc_array[i])
                                                if brand_html.upper().find(term_name.upper()) != -1:
                                                    term = doesprodattrexist(jsonprodattr['pa_brand'], brandterm['term_id'], 'pa_brand')
                                                    if term:
                                                        brandies_result.append((term, False))
                                            if brandies_result:
                                                if product_brand == '':
                                                    product_brand = brandies_result
                                                else:
                                                    product_brand = array_merge(product_brand, brandies_result)
                                        # --- Get categories from current scrape --- #
                                        if productmisc_array[(i-1)] == 'pa_category_html':
                                            caties = jsonprodattr['product_cat']
                                            caties_result = []
                                            #print('CATHTML: ' + str(productmisc_array[i]))
                                            for catterm in caties:
                                                term_name = catterm['name']
                                                cat_html = str(productmisc_array[i])
                                                if translate_pa_category_html != '':
                                                    langs_to_trnsl = translate_pa_category_html.split(',')
                                                    translator = Translator(to_lang=langs_to_trnsl[0], from_lang=langs_to_trnsl[1])
                                                    cat_html = translator.translate(cat_html)
                                                array_categorymaps = jsoncatmaps
                                                #print(type(cat_html))
                                                #print(type(term_name))
                                                if array_categorymaps:
                                                    #if hasattr(array_categorymaps, term_name):
                                                    if term_name in array_categorymaps:
                                                        #print('HERE!')
                                                        infliction_array = jsoncatmaps[term_name]['catinflections'].split(',')
                                                        for infliction in infliction_array:
                                                            #print('INFLICTION: ' + infliction)
                                                            #if cat_html.upper().find(r'\s'+infliction.upper()+r'\s') != -1:
                                                            regex = ''
                                                            if no_whitespace_htmlregex is True:
                                                                regex = ''+infliction.strip()+''
                                                            else:
                                                                regex = '\s'+infliction.strip()+'\s'
                                                            #print('INF_REGEX: ' + regex)
                                                            if re.search(regex, cat_html, flags=re.IGNORECASE):
                                                                #print('FOUND INFLICTION!')
                                                                term = doesprodattrexist(jsonprodattr['product_cat'], catterm['term_id'], 'product_cat')
                                                                if term:
                                                                    if not list(filter(lambda x: x[0]['term_id'] == term['term_id'], caties_result)):
                                                                        caties_result.append((term, False))
                                                                        cat_parents = term['ancestors']
                                                                        for parent_id in cat_parents:
                                                                            parent = doesprodattrexist(jsonprodattr['product_cat'], parent_id, 'product_cat')
                                                                            if not list(filter(lambda x: x[0]['term_id'] == parent['term_id'], caties_result)):
                                                                                caties_result.append((parent, False))
                                                #print('CATTERM: ' + term_name)
                                                #if cat_html.upper().find(r'\s'+term_name.upper()+r'\s') != -1:
                                                regex = ''
                                                if no_whitespace_htmlregex is True:
                                                    regex = ''+term_name.strip()+''
                                                else:
                                                    regex = '\s'+term_name.strip()+'\s'
                                                #print('CATTERM_REGEX: ' + regex)
                                                if re.search(regex, cat_html, flags=re.IGNORECASE):
                                                    #print('FOUND CATTERM!')
                                                    term = doesprodattrexist(jsonprodattr['product_cat'], catterm['term_id'], 'product_cat')
                                                    if term:
                                                        if not list(filter(lambda x: x[0]['term_id'] == term['term_id'], caties_result)):
                                                            caties_result.append((term, False))
                                                            cat_parents = term['ancestors']
                                                            for parent_id in cat_parents:
                                                                parent = doesprodattrexist(jsonprodattr['product_cat'], parent_id, 'product_cat')
                                                                if not list(filter(lambda x: x[0]['term_id'] == parent['term_id'], caties_result)):
                                                                    caties_result.append((parent, False))
                                            if caties_result:
                                                if product_categories == '':
                                                    product_categories = caties_result
                                                else:
                                                    product_categories = array_merge(product_categories, caties_result)
                                            #print('PA_CAT_HTML_CATS: '+json.dumps(product_categories))
                                        # --- Get color attributes from current scrape --- #
                                        if productmisc_array[(i-1)] == 'pa_color_html':
                                            colories = jsonprodattr['pa_color']
                                            colories_result = []
                                            for colorterm in colories:
                                                term_name = colorterm['name']
                                                color_html = str(productmisc_array[i])
                                                if color_html.upper().find(term_name.upper()) != -1:
                                                    term = doesprodattrexist(jsonprodattr['pa_color'], colorterm['term_id'], 'pa_color')
                                                    if term:
                                                        colories_result.append((term, False))
                                            if colories_result:
                                                if product_colors == '':
                                                    product_colors = colories_result
                                                else:
                                                    product_colors = array_merge(product_colors, colories_result)
                                        # --- Has the product sold out yet? --- #
                                        if productmisc_array[(i-1)] == 'sold_out_html':
                                            selector_one_string_two = prodmisc_backup.split(',')
                                            if len(selector_one_string_two) > 1:
                                                #soldoutselect = browser.find_by_css(selector_one_string_two[0].strip().encode().decode("unicode-escape"))
                                                soldoutselect = root.cssselect(str(selector_one_string_two[0]).strip().encode().decode("unicode-escape"))
                                                #productmisc_array[i] = soldoutselect[0].html
                                                productmisc_array[i] = str(etree.tostring(soldoutselect[0]))
                                                if productmisc_array[i].find(selector_one_string_two[1]) != -1:
                                                    soldouthtmlupdatemeta = True
                                                    price = '0.0 BUCKS'
                                                    price = price.replace(r'[^0-9,.]', '')
                                                    price = getmoneyfromtext(price)
                                                else:
                                                    soldouthtmlupdatemeta = False
                                    # --- Should we skip the first size alternative on information import? --- #
                                    if productmisc_array[(i-1)] == 'skip_first_size':
                                        if product_sizes != '':
                                            removed_size = product_sizes.pop(0)
                                # --> Fix sex for the product if it doesn't exist already! <-- #
                                if product_sex == '':
                                    product_sex = [(doesprodattrexist(jsonprodattr['pa_sex'], 'Male', 'pa_sex'), False),
                                                   (doesprodattrexist(jsonprodattr['pa_sex'], 'Female', 'pa_sex'), False)]
                                # --> Fix categories for the product! <-- #
                                if product_categories:
                                    existing_categories = product['category_ids'].copy()
                                    exist_cats = []
                                    if existing_categories and skip_exist_attr[6] != 1:
                                        #count = 0
                                        for cat in existing_categories.copy():
                                            term = doesprodattrexist(jsonprodattr['product_cat'], cat, 'product_cat')
                                            if term['slug'] == 'uncategorized' and len(product_categories) > 0:
                                                #del existing_categories[count]
                                                continue
                                            #existing_categories[count] = ((term, False))
                                            exist_cats.append((term, False))
                                            #count+=1
                                        #print('PRODCAT BEFORE: ' + json.dumps(product_categories))
                                        #print('EXISCAT BEFORE: ' + json.dumps(existing_categories))
                                        #product_categories = add_together_attrs(product_categories, existing_categories, 'product_cat')
                                        product_categories = add_together_attrs(product_categories, exist_cats, 'product_cat')
                                        #print('PRODCAT AFTER: ' + json.dumps(product_categories))
                                        #product_categories = product_categories + existing_categories   
                                    #SAVE CAT. IDS AND PRODUCT HERE IN REMOTE SITE
                                # --> Apply sizetype attributes where needed! <-- #
                                product_sizetypemiscname = sizetypemisc
                                if product_categories != '':
                                    array_catsizetypemaps = jsoncatsizetypemaps
                                    array_sizetypes = []
                                    for catsizetypemap in array_catsizetypemaps:
                                        finalcatsizetypes = catsizetypemap['finalcatsizetype'].split(',')
                                        catstosizetypes = catsizetypemap['catstosizetype'].split(',')
                                        product_category_names = []
                                        matching_cats = []
                                        for cat in product_categories:
                                            #print('CAT BEFORE SIZETYPEMISC: ' + json.dumps(cat))
                                            category_to_cast_id = cat[0]['term_id']
                                            term = doesprodattrexist(jsonprodattr['product_cat'], category_to_cast_id, 'product_cat')
                                            if term:
                                                if term['name'] not in product_category_names:
                                                    #print('ADDING ' + term['name'] + ' TO ARRAY!')
                                                    product_category_names.append(term['name'])
                                        for catstosizetype in catstosizetypes:
                                            #regex = u'(\b.*' + catstosizetype.strip() + '\b)'
                                            regex = '' + catstosizetype.strip() + ''
                                            filter_match = []
                                            filter_match = filter(lambda x: re.findall(regex, x, flags=re.IGNORECASE), product_category_names)
                                            #for match in filter_match: print('FILTER MATCH: ' + json.dumps(match))
                                            matching_cats = array_merge(matching_cats, list(filter_match))
                                        if matching_cats:
                                            #print('MATCHING CATS HERE!')
                                            size_type_terms = jsonprodattr['pa_sizetype'].copy()
                                            count = 0
                                            for size_type_term in size_type_terms:
                                                size_type_terms[count] = size_type_term['name']
                                                count+=1
                                            filtered_terms = []
                                            for finalcatsizetype in finalcatsizetypes:
                                                regex = '' + finalcatsizetype.strip() + ''
                                                filter_match = []
                                                filter_match = filter(lambda x: re.findall(regex, x, flags=re.IGNORECASE), size_type_terms)
                                                filtered_terms = array_merge(filtered_terms, list(filter_match))
                                            for filt_term in filtered_terms:
                                                #print('FILT TERM: ' + filt_term)
                                                term = doesprodattrexist(jsonprodattr['pa_sizetype'], filt_term, 'pa_sizetype')
                                                #print('SIZETYPE TO ADD: ' + json.dumps(term))
                                                if term:
                                                    array_sizetypes.append((term, False))     
                                    product_sizetypes = array_sizetypes
                                    if not product_sizetypes and product_sizes and not product_sizetypemiscname:
                                        product_sizetypemiscname = 'Other'
                                else:
                                    if product_sizes and not product_sizetypemiscname:
                                        product_sizetypemiscname = 'Other'
                                if product_sizetypemiscname:
                                    product_sizetypemiscs = []
                                    term = doesprodattrexist(jsonprodattr['pa_sizetypemisc'], product_sizetypemiscname, 'pa_sizetypemisc')
                                    if term:
                                        product_sizetypemiscs.append((term, False))
                                    else:
                                        namus = product_sizetypemiscname.strip()
                                        slugus = product_sizetypemiscname.strip().lower()
                                        term = {'term_id':-1, 'name':namus, 'slug':slugus, 'taxonomy':'pa_sizetypemisc'}
                                        product_sizetypemiscs.append((term, True))
                                # --> Fix/correct binds between existing product sizes and sizetypes(Including misc. sizetypes)! <-- #
                                if product_sizetypes and product_sizes:
                                    sizeid_col = product['sizetosizetypemaps']['size']
                                    sizetypeid_col = product['sizetosizetypemaps']['sizetype']
                                    product_size_col = []
                                    product_sizetype_col = []
                                    #for e in range(0, len(product_sizes)): product_size_col[e] = product_sizes[e][0]['term_id']
                                    #for e in range(0, len(product_sizetypes)): product_sizetype_col[e] = product_sizetypes[e][0]['term_id']
                                    for s in product_sizes: product_size_col.append(s[0]['term_id'])
                                    for s in product_sizetypes: product_sizetype_col.append(s[0]['term_id'])
                                    #count = 0
                                    #for sizeid in sizeid_col:
                                    #    sizeid_col[count] = (doesprodattrexist(jsonprodattr['pa_size'], sizeid, 'pa_size'), False)
                                    #    count+=1
                                    #count = 0
                                    #for sizetypeid in sizetypeid_col:
                                    #    sizetypeid_col[count] = (doesprodattrexist(jsonprodattr['pa_sizetype'], sizetypeid, 'pa_sizetype'), False)
                                    #    count+=1
                                    #CONVERT COMPARE ARRAYS
                                    #sizeid_col = [value for key, value in sizeid_col.items() if key == '']
                                    #sizetypeid_col = [value for key, value in sizetypeid_col.items() if key == '']
                                    #product_size_col = [value for key, value in product_sizes.items() if key == '']
                                    #product_sizetype_col = [value for key, value in product_sizetypes.items() if key == '']
                                    #SAVE VALUES FOR INSERT
                                    compare_sizeid = list(set(product_size_col) - set(sizeid_col))
                                    compare_sizetypeid = list(set(product_sizetype_col) - set(sizetypeid_col))
                                    if compare_sizetypeid and compare_sizeid:
                                        insert_sizetosizetype = []
                                        for sizetypeid_insert in compare_sizetypeid:
                                            #count = 0
                                            for sizeid_insert in compare_sizeid:
                                                insert_sizetosizetype.append((sizeid_insert, sizetypeid_insert, product['productid']))
                                                #insert_sizetosizetype[count] = (sizeid_insert, sizetypeid_insert, product['productid'])
                                                #count+=1
                                    #SAVE VALUES FOR REMOVAL
                                    compare_sizeid = list(set(sizeid_col) - set(product_size_col))
                                    compare_sizetypeid = list(set(sizetypeid_col) - set(product_sizetype_col))
                                    if compare_sizetypeid and compare_sizeid:
                                        remove_sizetosizetype = []
                                        for sizetypeid_remove in compare_sizetypeid:
                                            #count = 0
                                            for sizeid_remove in compare_sizeid:
                                                remove_sizetosizetype.append((sizeid_remove, sizetypeid_remove, product['productid']))
                                                #remove_sizetosizetype[count] = (sizeid_remove, sizetypeid_remove, product['productid'])
                                                #count+=1
                                if product_sizetypemiscs and product_sizes:
                                    sizeid_col = product['sizetosizetypemaps']['size_misc']
                                    compare_sizetypemiscid = product['sizetosizetypemaps']['sizetype_misc']
                                    product_size_col = []
                                    product_sizetypemisc_col = []
                                    #for e in range(0, len(product_sizes)): product_size_col[e] = product_sizes[e][0]['term_id']
                                    #for e in range(0, len(product_sizetypes)): product_sizetypemisc_col[e] = product_sizetypemiscs[e][0]['term_id']
                                    for s in product_sizes: product_size_col.append(s[0]['term_id'])
                                    for s in product_sizetypemiscs: product_sizetypemisc_col.append(s[0]['term_id'])
                                    #count = 0
                                    #for sizeid in sizeid_col:
                                    #    sizeid_col[count] = (doesprodattrexist(jsonprodattr['pa_size'], sizeid, 'pa_size'), False)
                                    #    count+=1
                                    #count = 0
                                    #for sizetypemiscid in compare_sizetypemiscid:
                                    #    compare_sizetypemiscid[count] = (doesprodattrexist(jsonprodattr['pa_sizetypemisc'], sizetypemiscid, 'pa_sizetypemisc'), False)
                                    #    count+=1
                                    #SAVE VALUES FOR INSERT
                                    compare_sizeid = list(set(product_size_col) - set(sizeid_col))
                                    compare_sizetypemiscid = list(set(product_sizetypemisc_col) - set(compare_sizetypemiscid)) 
                                    if compare_sizetypemiscid and compare_sizeid:
                                        insert_sizetosizetypemisc = []
                                        for sizetypemiscid_insert in compare_sizetypemiscid:
                                            #count = 0
                                            for sizeid_insert in compare_sizeid:
                                                insert_sizetosizetypemisc.append((sizeid_insert, sizetypemiscid_insert, product['productid']))
                                                #insert_sizetosizetypemisc[count] = (sizeid_insert, sizetypemiscid_insert, product['productid'])
                                                #count+=1
                                    #SAVE VALUES FOR REMOVAL
                                    compare_sizeid = list(set(sizeid_col) - set(product_size_col))
                                    compare_sizetypemiscid = list(set(compare_sizetypemiscid) - set(product_sizetypemisc_col))
                                    if compare_sizetypemiscid and compare_sizeid:
                                        remove_sizetosizetypemisc = []
                                        for sizetypemiscid_remove in compare_sizetypemiscid:
                                            #count = 0
                                            for sizeid_remove in compare_sizeid:
                                                remove_sizetosizetypemisc.append((sizeid_remove, sizetypemiscid_remove, product['productid']))
                                                #remove_sizetosizetypemisc[count] = (sizeid_remove, sizetypemiscid_remove, product['productid'])
                                                #count+=1
                                # --> Map current sizes to pre-destined sizes depending on sizetype! <-- #
                                if product_sizetypes and product_sizes:
                                    #remove_remaining_sizes = False
                                    for sizemap in jsonsizemaps:
                                        sizemap_sizetypes = sizemap['sizetypestofilter'].split(',')
                                        for sizemap_sizetype in sizemap_sizetypes:
                                            sizemap_sizetype = re.sub(r'\-\d+', '', sizemap_sizetype.strip())
                                            for sizetype in product_sizetypes:
                                                if sizetype[0]['name'] == sizemap_sizetype:
                                                    # --> Check if there are any sex-specific sizes to map!
                                                    if len(product_sex) == 1:
                                                        sex_name = product_sex[0][0]['name']
                                                        split_sizetomaps = sizemap['sizestomap'].split(',')
                                                        count = 0
                                                        for sizetomap in split_sizetomaps.copy():
                                                            if re.search(r'\(M\)', sizetomap) and sex_name == 'Male':
                                                                split_sizetomaps[count] = re.sub(r'\(M\)', '', sizetomap)
                                                            elif re.search(r'\(F\)', sizetomap) and sex_name == 'Female':
                                                                split_sizetomaps[count] = re.sub(r'\(F\)', '', sizetomap)
                                                            count += 1
                                                        sizemap['sizestomap'] = ','.join(split_sizetomaps)
                                                        #print(sizemap['sizestomap'])
                                                    #found_sizenames = []
                                                    #split_sizetomaps = sizemap['sizestomap'].split(',')
                                                    #for sizetomap in split_sizetomaps.copy():
                                                    #found_sizenames = list(filter(lambda x: re.search(x[0]['name'], sizemap['sizestomap']), product_sizes))
                                                    #for prod_size in product_sizes:
                                                    #    found_sizenames = list(filter(lambda x: prod_size[0]['name'] == x, sizemap['sizestomap']))
                                                    split_sizetomaps = sizemap['sizestomap'].split(',')
                                                    for sizetomap in split_sizetomaps.copy():
                                                        found_sizenames = list(filter(lambda x: x[0]['name'].strip().lower() == sizetomap.strip().lower(), product_sizes))
                                                        if found_sizenames:
                                                            finalterm = doesprodattrexist(jsonprodattr['product_cat'], sizemap['finalsize'].strip(), 'product_cat')
                                                            if finalterm != 0:
                                                                product_sizes.append((finalterm, False))
                                                            else:
                                                                finalsizename = sizemap['finalsize'].strip()
                                                                finalsizeslug = slugify(finalsizename.strip())
                                                                new_finalterm = {'term_id':-1, 'name':finalsizename, 'slug':finalsizeslug, 'taxonomy':'pa_size'}
                                                                product_sizes.append((new_finalterm, True))
                                                            #for size_to_remove in sizemap['sizestomap'].split(','):
                                                            for size_to_remove in split_sizetomaps:
                                                                size_to_remove = size_to_remove.strip().lower()
                                                                product_sizes = list(filter(lambda x: x[0]['name'].strip().lower() != size_to_remove, product_sizes))
                                                            #print(json.dumps(product_sizes))
                                                            break
                                # --> Apply color, size, sex and brand to the product! (Filter the attributes before save)
                                # --> (Filter the attributes before database save)
                                attributes = []
                                attribute_pos = 1 
                                if product_brand:
                                    skip_domain_name = False
                                    if website['productmisc']:
                                        output = re.search(r'(skip_domainbrand_if_found)', website['productmisc'])
                                        if output is not None and len(output.group(0)) > 0:
                                            skip_domain_name = True
                                    brand_values = product['attributes']['brand']
                                    if brand_values and skip_exist_attr[0] != 1:
                                        existing_brands = re.split(',\s*', brand_values)
                                        exist_brands = []
                                        #count = 0
                                        for brand in existing_brands.copy():
                                            '''if skip_domain_name is True:
                                                if domain_name != '':
                                                    if brand.upper().find(domain_name.upper()) != -1:
                                                        del existing_brands[count]
                                                        continue
                                            brand = doesprodattrexist(jsonprodattr['pa_brand'], brand, 'pa_brand')
                                            existing_brands[count] = (brand, False)
                                            count+=1'''
                                            if skip_domain_name is True:
                                                if domain_name != '':
                                                    if brand.upper().find(domain_name.upper()) != -1:
                                                        #del existing_brands[count]
                                                        continue
                                            brand = doesprodattrexist(jsonprodattr['pa_brand'], brand, 'pa_brand')
                                            notlist = list(filter(lambda x: x[0]['name'].lower() == brand['name'].lower(), exist_brands))
                                            if not notlist:
                                                exist_brands.append((brand, False))
                                            else:
                                                #del existing_brands[count]
                                                exist_brands = list(filter(lambda x: x[0]['name'].lower() != brand['name'].lower(), exist_brands))
                                                #exist_brands.append(notlist[0])
                                                continue
                                            #count+=1
                                        if skip_domain_name is True and len(product_brand) > 0 and len(exist_brands) > 0:
                                            product_brand = exist_brands
                                        else:
                                            #product_brand = product_brand + existing_brands
                                            product_brand = add_together_attrs(product_brand, exist_brands, 'pa_brand')
                                        #print('FINAL BRANDS: ' + json.dumps(product_brand))
                                    attributes.append({'name':'Brand', 'options':product_brand, 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                if product_colors:
                                    color_values = product['attributes']['color']
                                    if color_values and skip_exist_attr[1] != 1:
                                        existing_colors = re.split(',\s*', color_values)
                                        count = 0
                                        for color in existing_colors:
                                            color = doesprodattrexist(jsonprodattr['pa_color'], color, 'pa_color')
                                            existing_colors[count] = (color, False)
                                            count+=1
                                        #product_colors = product_colors + existing_colors
                                        product_colors = add_together_attrs(product_colors, existing_colors, 'pa_color')
                                    attributes.append({'name':'Color', 'options':product_colors, 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                if product_sex:
                                    sex_values = product['attributes']['sex']
                                    if sex_values and skip_exist_attr[2] != 1:
                                        existing_sex = re.split(',\s*', sex_values)
                                        count = 0
                                        for sex in existing_sex:
                                            sex = doesprodattrexist(jsonprodattr['pa_sex'], sex, 'pa_sex')
                                            existing_sex[count] = (sex, False)
                                            #existing_sex[count] = sex['term_id']
                                            count+=1
                                        #product_sex = product_sex + existing_sex
                                        #print('FINAL SEX BEFORE: ' + json.dumps(product_sex))
                                        product_sex = add_together_attrs(product_sex, existing_sex, 'pa_sex')
                                        #print('FINAL SEX AFTER: ' + json.dumps(product_sex))
                                    attributes.append({'name':'Sex', 'options':product_sex, 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                if product_sizes:
                                    size_values = product['attributes']['size']
                                    if size_values and skip_exist_attr[3] != 1:
                                        existing_sizes = re.split(',\s*', size_values)
                                        count = 0
                                        for size in existing_sizes:
                                            size = doesprodattrexist(jsonprodattr['pa_size'], size, 'pa_size')
                                            existing_sizes[count] = (size, False)
                                            count+=1
                                        #product_sizes = product_sizes + existing_sizes
                                        #print('FINAL SIZES BEFORE: ' + json.dumps(product_sizes))
                                        product_sizes = add_together_attrs(product_sizes, existing_sizes, 'pa_size')
                                        #print('FINAL SIZES AFTER: ' + json.dumps(product_sizes))
                                    attributes.append({'name':'Size', 'options':product_sizes, 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                if product_sizetypes:
                                    sizetype_values = product['attributes']['sizetype']
                                    if sizetype_values and skip_exist_attr[4] != 1:
                                        existing_sizetypes = re.split(',\s*', sizetype_values)
                                        count = 0
                                        for sizetype in existing_sizetypes:
                                            sizetype = doesprodattrexist(jsonprodattr['pa_sizetype'], sizetype, 'pa_sizetype')
                                            existing_sizetypes[count] = (sizetype, False)
                                            count+=1
                                        #product_sizetypes = product_sizetypes + existing_sizetypes
                                        product_sizetypes = add_together_attrs(product_sizetypes, existing_sizetypes, 'pa_sizetype')
                                    attributes.append({'name':'Sizetype', 'options':product_sizetypes, 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                if product_sizetypemiscs:
                                    sizetypemisc_values = product['attributes']['sizetypemisc']
                                    if sizetypemisc_values and skip_exist_attr[5] != 1:
                                        existing_sizetypemiscs = re.split(',\s*', sizetypemisc_values)
                                        count = 0
                                        for sizetypemisc in existing_sizetypemiscs:
                                            sizetypemisc = doesprodattrexist(jsonprodattr['pa_sizetypemisc'], sizetypemisc, 'pa_sizetypemisc')
                                            existing_sizetypemiscs[count] = (sizetypemisc, False)
                                            count+=1
                                        #product_sizetypemiscs = product_sizetypemiscs + existing_sizetypemiscs
                                        product_sizetypemiscs = add_together_attrs(product_sizetypemiscs, existing_sizetypemiscs, 'pa_sizetypemisc')
                                    attributes.append({'name':'Sizetypemisc', 'options':product_sizetypemiscs, 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                attributes_to_store = attributes
                                catstoaddresult = product_categories
                                # --- Make sure to empty all the already-checked bits and join the productmisc. bits back together! --- #
                                ###
                                ###
                                #pass
                            except:
                                #print("Error when scraping misc. product information for product ID " + product['productid'] + ": " + sys.exc_info()[0] + " occured!")
                                print(traceback.format_exc())
                        # >>> CHECK FOR PRODUCT PROPERITES IN TITLE(IF ENABLED) <<< #
                        if website['lookforprodpropintitle'] == '1':
                            try:
                                termies = [[], [], []]
                                termies[0] = jsonprodattr['pa_brand']
                                termies[1] = jsonprodattr['pa_color']
                                termies[2] = jsonprodattr['pa_sex']
                                termies_result = [[], [], []]
                                for i in range(3):
                                    for term in termies[i]:
                                        term_name = term['name']
                                        product_name = product['name']
                                        if product_name.upper().find(term_name.upper()) != -1:
                                            termies_result[i].append((doesprodattrexist(jsonprodattr[term['taxonomy']], term['term_id'], term['taxonomy']), False))
                                attributes = []
                                attribute_pos = 1
                                if termies_result[0] and skip_exist_attr_prodtitle[0] != 1:
                                    brand_values = product_brand
                                    skip_domain_name = False
                                    if website['productmisc']:
                                        output = re.search(r'(skip_domainbrand_if_found)', website['productmisc'])
                                        if output is not None and len(output.group(0)) > 0:
                                            skip_domain_name = True
                                    if brand_values:
                                        #existing_brands = re.split(',\s*', brand_values)
                                        existing_brands = brand_values
                                        ###count = 0
                                        ###for brand in existing_brands:
                                        ###    existing_brands[count] = (brand, False)
                                        ###    count+=1
                                        termies_result[0] = array_merge(termies_result[0], existing_brands)
                                        if skip_domain_name and domain_name != '' and len(termies_result[0]) > 1:
                                            termies_result[0] = list(filter(lambda x: x[0]['name'].upper().find(domain_name.upper()) == -1, termies_result[0]))
                                    attributes.append({'name':'Brand', 'options':termies_result[0], 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                else:
                                    brand_values = product_brand
                                    if brand_values:
                                        #existing_brands = re.split(',\s*', brand_values)
                                        existing_brands = brand_values
                                        ###count = 0
                                        ###for brand in existing_brands:
                                        ###    existing_brands[count] = (brand, False)
                                        ###    count+=1
                                        product_brand = existing_brands
                                        attributes.append({'name':'Brand', 'options':product_brand, 'position':attribute_pos, 'visible':1, 'variation':1})
                                        attribute_pos+=1
                                if termies_result[1] and skip_exist_attr_prodtitle[1] != 1:
                                    color_values = product_colors
                                    if color_values:
                                        #existing_colors = re.split(',\s*', color_values)
                                        existing_colors = color_values
                                        ###count = 0
                                        ###for color in existing_colors:
                                        ###    existing_colors[count] = (color, False)
                                        ###    count+=1
                                        termies_result[1] = array_merge(termies_result[1], existing_colors)
                                    attributes.append({'name':'Color', 'options':termies_result[1], 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                else:
                                    color_values = product_colors
                                    if color_values:
                                        #existing_colors = re.split(',\s*', color_values)
                                        existing_colors = color_values
                                        ###count = 0
                                        ###for color in existing_colors:
                                        ###    existing_colors[count] = (color, False)
                                        ###    count+=1
                                        product_colors = existing_colors
                                        attributes.append({'name':'Color', 'options':product_colors, 'position':attribute_pos, 'visible':1, 'variation':1})
                                        attribute_pos+=1
                                if termies_result[2] and skip_exist_attr_prodtitle[2] != 1:
                                    sex_values = product_sex
                                    if sex_values:
                                        #existing_sex = re.split(',\s*', sex_values)
                                        existing_sex = sex_values
                                        ###count = 0
                                        ###for sex in existing_sex:
                                        ###    existing_sex[count] = (sex, False)
                                        ###    count+=1
                                        termies_result[2] = array_merge(termies_result[2], existing_sex)
                                    attributes.append({'name':'Sex', 'options':termies_result[2], 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                else:
                                    sex_values = product_sex
                                    #print('SEX VALUES, INPRODTITLE:')
                                    #for sex in sex_values: print(sex)
                                    if sex_values:
                                        #existing_sex = re.split(',\s*', sex_values)
                                        existing_sex = sex_values
                                        ###count = 0
                                        ###for sex in existing_sex:
                                        ###    existing_sex[count] = (sex, False)
                                        ###    count+=1
                                        product_sex = existing_sex
                                        attributes.append({'name':'Sex', 'options':product_sex, 'position':attribute_pos, 'visible':1, 'variation':1})
                                        attribute_pos+=1
                                size_values = product_sizes
                                if size_values:
                                    #existing_sizes = re.split(',\s*', size_values)
                                    existing_sizes = size_values
                                    product_sizes = existing_sizes
                                    attributes.append({'name':'Size', 'options':product_sizes, 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                sizetype_values = product_sizetypes
                                if sizetype_values:
                                    #existing_sizetypes = re.split(',\s*', sizetype_values)
                                    existing_sizetypes = sizetype_values
                                    product_sizetypes = existing_sizetypes
                                    attributes.append({'name':'Sizetype', 'options':product_sizetypes, 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                sizetypemisc_values = product_sizetypemiscs
                                if sizetypemisc_values:
                                    #existing_sizetypemiscs = re.split(',\s*', sizetypemisc_values)
                                    existing_sizetypemiscs = sizetypemisc_values
                                    product_sizetypemiscs = existing_sizetypemiscs
                                    attributes.append({'name':'Sizetypemisc', 'options':product_sizetypemiscs, 'position':attribute_pos, 'visible':1, 'variation':1})
                                    attribute_pos+=1
                                attributes_to_store = attributes
                                # --> Look after categories in the product title!
                                category_terms = jsonprodattr['product_cat']
                                category_result = []
                                for term in category_terms:
                                    term_name = term['name']
                                    product_name = product['name']
                                    array_categorymaps = jsoncatmaps
                                    if array_categorymaps:
                                        if term_name in array_categorymaps:
                                            infliction_array = jsoncatmaps[term_name]['catinflections'].split(',')
                                            for infliction in infliction_array:
                                                if no_whitespace_prodtitleregex is True:
                                                    regex = ''+infliction.strip()+''
                                                else:
                                                    regex = '\s'+infliction.strip()+'\s'
                                                if re.search(regex, product_name, flags=re.IGNORECASE):
                                                    term = doesprodattrexist(jsonprodattr['product_cat'], term['term_id'], 'product_cat')
                                                    if term:
                                                        if not list(filter(lambda x: x[0]['term_id'] == term['term_id'], category_result)):
                                                            category_result.append((term, False))
                                                    cat_parents = term['ancestors']
                                                    for parent_id in cat_parents:
                                                        parent = doesprodattrexist(jsonprodattr['product_cat'], parent_id, 'product_cat')
                                                        if not list(filter(lambda x: x[0]['term_id'] == parent['term_id'], category_result)):
                                                            category_result.append((parent, False))
                                    if no_whitespace_prodtitleregex is True:
                                        regex = ''+term_name.strip()+''
                                    else:
                                        regex = '\s'+term_name.strip()+'\s'
                                    if re.search(regex, product_name, flags=re.IGNORECASE):
                                        term = doesprodattrexist(jsonprodattr['product_cat'], term['term_id'], 'product_cat')
                                        if term:
                                            if not list(filter(lambda x: x[0]['term_id'] == term['term_id'], category_result)):
                                                category_result.append((term, False))
                                        cat_parents = term['ancestors']
                                        for parent_id in cat_parents:
                                            parent = doesprodattrexist(jsonprodattr['product_cat'], parent_id, 'product_cat')
                                            if not list(filter(lambda x: x[0]['term_id'] == parent['term_id'], category_result)):
                                                category_result.append((parent, False))
                                if category_result:
                                    existing_categories = product['category_ids'].copy()
                                    exist_cats = []
                                    #print(json.dumps(existing_categories))
                                    if existing_categories and skip_exist_attr_prodtitle[3] != 1:
                                        #count = 0
                                        for cat in existing_categories.copy():
                                            term = doesprodattrexist(jsonprodattr['product_cat'], cat, 'product_cat')
                                            #print(json.dumps(term))
                                            #print(cat)
                                            if (term['slug'] == 'uncategorized' and len(category_result) > 0)\
                                            or list(filter(lambda x: x[0]['term_id'] == term['term_id'], category_result)):
                                                #del existing_categories[count]
                                                continue
                                            #existing_categories[count] = ((term, False))
                                            exist_cats.append((term, False))
                                            #count+=1 
                                        category_result = array_merge(category_result, exist_cats)
                                    #print('PRODCATSFINAL_PRODTITLE: ' + json.dumps(product_categories))
                                    #print('CATRESULTS_PRODTITLE: ' + json.dumps(category_result))
                                    if product_categories != '':
                                        #product_categories = array_merge(product_categories, category_result)
                                        for result in category_result:
                                            if not list(filter(lambda x: x[0]['term_id'] == result[0]['term_id'], product_categories)):
                                                product_categories.append(result)
                                    else:
                                        product_categories = category_result
                                catstoaddresult = product_categories
                            except:
                                #print("Error when looking after prod. properties in title for product ID " + product['productid'] + ": " + sys.exc_info()[0] + " occured!")
                                print(traceback.format_exc())
                        # >>> MAKE PRICES NUMERIC <<< #
                        price = getmoneyfromtext(price)
                        salesprice = getmoneyfromtext(salesprice)
                        # >>> STORE PRODUCT VALUES IN MORPH.IO DATABASE <<< #
                        scraperwiki.sqlite.save(unique_keys=['productid'],\
                                                data={'productid': product['productid'],\
                                                      'url': product['url'],\
                                                      'domain': product['domain'],\
                                                      'price': price,\
                                                      'salesprice': salesprice,\
                                                      'domainmisc':  json.dumps(domainmisc_array),\
                                                      'prodlogurls': json.dumps(prodlog_image_urls),\
                                                      'prodlogurl': productlogourl,\
                                                      'finalimgurls': json.dumps(images),\
                                                      'validimgurls': json.dumps(image_urls_valid),\
                                                      'imgurls': json.dumps(image_urls),\
                                                      'notfound': notfound,\
                                                      'notavailable': notavailable,\
                                                      'removeon404': shouldremoveonnotfound,\
                                                      'soldoutfix': soldoutupdatemeta,\
                                                      'soldouthtmlfix': soldouthtmlupdatemeta,\
                                                      'catstoaddresult': json.dumps(catstoaddresult),\
                                                      'attributes': json.dumps(attributes_to_store),\
                                                      'sizetypemapsqls': json.dumps([insert_sizetosizetype,\
                                                                 remove_sizetosizetype,\
                                                                 insert_sizetosizetypemisc,\
                                                                 remove_sizetosizetypemisc])})
                            #browser.quit()
                        totalscrapedcount = totalscrapedcount + 1
                    except WebDriverException:
                        print('Chrome not running properly - The product will be rescraped again!')
                        jsonprods.append(product)
                        time.sleep(2)
                        continue
                    except:
                        #print("Error: " + sys.exc_info()[0] + " occured!")
                        print(traceback.format_exc())
                        continue
                else:
                    continue
        if website['productmisc'] != '':
            website['productmisc'] = orig_prodmisc
    offset = offset + limit
    r = requests.get(wp_connectwp_url + str(offset) + '/' + str(limit) + '/', headers=headers)
    jsonprods = r.json()
    #print(str(offset) + ' products has been scraped so far!')
    print(str(totalscrapedcount) + ' products has been scraped so far!')
