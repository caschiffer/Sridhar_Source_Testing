# -*- coding: utf-8 -*-
"""
Created on Thu Feb  9 08:57:01 2017

@author: yoann.randriamihaja
v2.0: add google news RSS feed from Jon K.
v3.0: add fiercepharma and fiercebiotech RSS feeds
v5.0: add OSS check for html PR title so that they are not indexed twice
v6.0: add title current date check, non-keyword-unique-url check, and multiple keyword adapted urls.
v7.0: add new RSS links, automated RSS link ingestion
v8.0: redundant title check and path designation for EC2 instance corrections, 
non functional RSS sources collection and csv print out
v9.0: bugs associated with new automated RSS source incorporation repair,
bugs in check title function causing html access errors rectified, 
url formatting in check title function repaired - CS
v10.0: incorporated new RSS title check for links from all RSS sources within 15 minute time span - CS
V11.0: added saving of PR source url to a SQL DB and commented out unused move.sh scripts - YMR
v11.5: added additional RSS feeds, added additional conditions to date check
 provided additional documentation, expanded columns of A array - CS
v12.0: updated saving of PR source url to a SQL DB - YMR 
v13.0: updated RSS feeds to include businesswire - CS 1/3/2020
"""


#import csv library
import csv
import time
import numpy as np
import os
import socket
import feedparser
from datetime import datetime
import ast
from collections import Counter 

import subprocess
import shlex

import concurrent.futures

import pandas as pd

import random
import urllib.request
from urllib.parse import unquote
import html5lib
import lxml
from urllib.parse import urlencode


from google import google
from google.modules.utils import _get_search_url, get_html, get_pdf, get_pdf_summary
from google.modules.standard_search import _get_link

import re
from bs4 import BeautifulSoup
from random import randint

from pathlib import Path
import urllib.parse
import json
from fuzzywuzzy import fuzz 

pd.set_option("display.width", None)

import sys

#path = r'\\ROIAWS1CRSG01\roivant-compres-copy\computationalresearch\for Yoann\U_drive\Coding\Python\web-scrapping\google-news-search-Feb-17\EC2 version'.replace('\\', '/') + '/'
#sys.path.append(path)
sys.path.append("/root/PR_webscraping/")
#sys.path.append("/root/python_code/RSS_Feed_Scrapes/")
import daily_check_v2

from daily_check_v2 import link_check, directory_creator, get_root_path
import MySQLdb
from pandas import DataFrame 

timestamp = datetime.now().strftime("%Y-%m-%d")

start_time = time.time()

#timeout in seconds
timeout=30
socket.setdefaulttimeout(timeout)

#path = "R:/Business Development/Computational Research/for Yoann/U_drive/Coding/Python/web-scrapping/google-news-search-Feb-17/EC2 version/"
#path = "C:/Users/krithika.kuppusamy/Documents/Important/"
path = '/root/PR_webscraping/'
#path = '/root/python_code/RSS_Feed_Scrapes/'
#path = 'C:/Users/cody.schiffer/Desktop/RSS_Improvement_Sample/RSS/'

date = time.strftime("%d-%m-%Y_%H_%M")
#path = 'U:/Yoann/Coding/Python/web-scrapping/google-news-search-Feb-17/debug/'


#html_directory, pdf_directory = directory_creator("RSS") #Krithika wrong folder creation

#creates the daily directory to save the PR pdf when PR is not an html file
pdf_folder = "pdf/" + date + "_RSS/"
pdf_directory = os.path.dirname(path + pdf_folder)
if not os.path.exists(pdf_directory):
    os.makedirs(pdf_directory)

#creates the daily directory to save the PR html
html_folder = "PR_html_saving/" + date + "_RSS/"
html_directory = os.path.dirname(path + html_folder)
if not os.path.exists(html_directory):
    os.makedirs(html_directory)



f = open(path + "phase3_ready_pharma_companies.csv")
#f = open( path + "list of always failing PR web sites.csv")
csv_f = csv.reader(f)

#initialize a blank list
data = []

#append each row of the csv file to the list data
for row in csv_f:
    data.append(row)

#save the headers to Header and remove them for the list    
Header = data[0]
data.pop(0)
Header.append("PR_Links_cache")

#https://github.com/abenassi/Google-Search-API


#line break cleaning
def line_break_cleaning(s):
    s=s.replace('\r\n','')
    s=s.replace('\n','')
    s=s.replace('\t',' ')
    s=re.sub(' +',' ',s) #remove consecutve spaces
    s=s.strip()
    return s


def check_title_OSS(title, fuzzy):
    #url = 'http://10.115.1.31:8983/solr/core1/select?fl=id%20title&indent=on&q='
    url = 'http://10.115.1.195:8983/solr/opensemanticsearch/select?fl=id,%20title_txt&q='

    if '"' not in title:
        query = '"' + title + '"'
        fuzzy_query = title #set up for fuzzy query
    else:
        query = title
        fuzzy_query = title.replace('"', '') #if necessary adjust for fuzzy query formatting
        
        
    print('this is the title --->', title)
    if fuzzy == 'no':
        params_solr = {'q':query.encode('utf8')} #query encoding                                             
        params_solr = urlencode(params_solr)
        params_solr = params_solr.replace('q=','title_txt:')
        search_url = url + params_solr +'&wt=json' #url formatting
        print(search_url, '---- this is the check title search url')
        html = get_html(search_url)

        
        if html:
            #print('yah')
            d = json.loads(html.decode('utf-8')) #parse a string/unicode object into a json object
            if len(d['response']['docs']) == 0:
                print('we will save', title)
                return False
            for j,doc in enumerate(d['response']['docs']):
                if len(doc) > 0:
                    print('this is the search url --->' , search_url,' it is longer than 0 characters')
                    print(title, 'is a redundant title!')
                    return True #True indicates document is redundant and should not be indexed
                    # explicit redundancy check is below
    #                        title_OSS = doc['title'][0]
    #                        title_OSS = line_break_cleaning(title_OSS)
    #                        title = line_break_cleaning(title)
    #                        if str(title_OSS) == str(title):
    #                            print('{}'.format(title) + ' is a redundant document!')
    #                            return True
    #                        else: 
    #                            return False #False indicates the document is new and should be indexed
                else:
                    print('we will save', title)
                    return False #False indicates the document is new and should be indexed    

    else:
        params_solr_fuzzy = {'q': fuzzy_query.encode('utf-8')} #fuzzyquery  encoding
        params_solr_fuzzy = urlencode(params_solr_fuzzy)
        params_solr_fuzzy = params_solr_fuzzy.replace('q=','title_txt:')
        search_url_fuzzy = url + params_solr_fuzzy + '&wt=json' #url formatting with fuzzy query
        html_fuzzy = get_html(search_url_fuzzy) 
        
        
        if html_fuzzy:
            #print('yah fuzzy')
            d_fuzzy = json.loads(html_fuzzy.decode('utf-8'))
            if len(d['response']['docs']) == 0:
                print('we will save', title)
                return False
            for j,doc in enumerate(d_fuzzy['response']['docs']):
                try:
                    if len(doc) > 0:
                        print('this is the search url --->' , search_url,' it is longer than 0 characters')
                        title_OSS = doc['title_txt'][0]
                        title_OSS = line_break_cleaning(title_OSS)
                        title = line_break_cleaning(title)
                        fuzz_ratio = fuzz.partial_ratio(title, title_OSS)
                        if fuzz_ratio > .90:
                            #print(title_OSS_collection)
                            print('{}'.format(title) + ' is a redundant document!')
                            return True #True indicates document is redundant and should not be indexed
                        else: 
                            return False #False indicates the document is new and should be intdexed
                    else:
                        return False
                except: 
                    print('{}'.format(search_url_fuzzy) + ' html failure -- examine title extraction') # Highlights which titles are failing in console
                    return False

""" Get PR function """

def get_PR(A, row, f, k, col, version, failed):
    #print("get_PR function is accessed")
    list_of_failed_urls = []
    if version == 'PR':
        start = 2
    else:
        start = 1
       
    if k>0: #(skip the header)
        pdf_count = 0
        html_count = 0
        for x in range(start, col):
            #print("we are hitting start, col")
            flag = False
            if row[x]:
                #print("raw row[", str(x), "]: ", row[x])

                if row[x].startswith('/'):
                    if row[x].startswith('//'):
                        url = 'http://' + row[x].lstrip('//')

                else:
                    if row[x].startswith('./'):
                        root_path = get_root_path(row[1], 1)
                        url = root_path + row[x].lstrip('.')
                    else:
                        url = row[x]

                modified_url = urllib.parse.quote_plus(url,'/:!#$%^&*()_-+=[]{}?', 'utf-8')
                

                html_name = row[0] + "_PR" + str(x-1) + "_" + date + ".html"
                html_res = get_html(modified_url)
                
                
                    
                if html_res:
                    #print("this is the modified_url of ", modified_url)

                    if b'PDF' not in html_res[:6]: #is this checking the doctype must look into further
                        
                        #check that the document is not alread indexed
                        #get html title
                        soup = BeautifulSoup(html_res, "html.parser")
                        try:
                            title = soup.find('title').string
                        except: 
                            title = ''
                        
                
                        
                        #search for the title on OSS with except statement
                        try:
                            if check_title_OSS(title,fuzzy = 'no') == False: #download only if the title is not in OSS
                            # print('title check indicates', title, ' to be indexed')
                                with open(html_directory + "/" + html_name, 'wb') as out_file:
                                    out_file.write(html_res)
                                html_count += 1
                                flag = True
                                #total[row[0]] -= 1
                                #return total
                        except:
                            ## If check_title_OSSAssume file is not already indexed and download accordingly
                            print('check_title_oss function failure --- likely due to solr query format')
                            with open(html_directory + "/" + html_name, 'wb') as out_file:
                                out_file.write(html_res)
                            html_count += 1
                            flag = True

                    
                    else:
                        #print("\n------we will attempt to download a PDF instead\n")
                        pdf_name =  row[0] + "_PR" + str(pdf_count) + "_" + date + ".pdf"
                        pdf_res = get_pdf(modified_url)
                        
                        pdf = 1
                        pdf_count += 1

                        if pdf_res:
                            with open(pdf_directory + "/" + pdf_name, 'wb') as out_file:
                                out_file.write(pdf_res)
                            flag = True
                            #total[row[0]] -= 1
                            #return total

                if not flag:
                    list_of_failed_urls.append(modified_url)
    failed = list_of_failed_urls #returns list of failed urls


      
ik = 0
ii = 0

col=350
A=np.empty((len(data)+1,col),dtype=object) #creates an array of object
A.fill([])  #change object type to list

A_summary=np.empty((len(data)+1,col*2),dtype=object) #creates an array of object
A_summary.fill([])  #change object type to list

#creates an array of failed link access
A_FL=np.empty((1000,2),dtype=object) #creates an array of object
A_FL.fill([])  #change object type to list

#creates an array of failed link access
A_timing=np.empty((2000,2),dtype=object) #creates an array of object
A_timing.fill([])  #change object type to list         
         
"""

For each company, go to their press release website (or to PRNewsWire.com)
download all the links within the page
compare the list of links with a previous reference to check for updates

"""         






A[0][0]='Company name'
A[0][1]='Company\'s PR website'
A_FL[0][0]='Company name and failed links'
for x in range(2, col):
    A[0][x]='New PR links'
"""
This part of the code will compare the new PR to the reference one (if any) for updates
It will generate a PR summary
"""

########################
"""
This portion of the code downloads RSS feeds and compare them to the last reference for new PRs
"""

"""Some feeds require dynamic date selection due to omission of front0 in single digit dates
   See if-else statements built into specific website scrapping sections"""
#########################
repeated_rss_titles_check = []
currentdate = datetime.now().strftime('%d %b %Y') #setting current date and frmt
#
prnw_ls = []    #list to hold the PRNewsWire RSS links
prnw_ls2 = []
prnw_ls3 = []
prnw_ls4 = []

d = feedparser.parse('http://www.prnewswire.com/rss/health/clinical-trials-medial-discoveries-news.rss') #Clinical Trials & Medical Discoveries

#print("entries in prnewswire rss feed \n")
for post in d.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        prnw_ls.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass
                  
    
d1 = feedparser.parse('http://www.prnewswire.com/rss/health/medical-pharmaceuticals-news.rss') #medical and pharmaceutical

for post in d1.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        prnw_ls2.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass
                    
d2 = feedparser.parse('http://www.prnewswire.com/rss/health/pharmaceuticals-news.rss') #pharmaceutical
for post in d2.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        prnw_ls3.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass


ct_ls = []    #list to hold the ct.gov RSS links
ct_ls2 = []


#clinicaltrial.gov search with empty query Show studies that were added or modified in the last 14 days
d3 = feedparser.parse('https://clinicaltrials.gov/ct2/results/rss.xml?rcv_d=&lup_d=14&show_rss=Y&sel_rss=mod14&count=100') 
for post in d3.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        ct_ls.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

#clinicaltrial.gov search with empty query Show studies that were first received in the last 14 days
d4 = feedparser.parse('https://clinicaltrials.gov/ct2/results/rss.xml?rcv_d=14&lup_d=&show_rss=Y&sel_rss=new14&count=100') 
for post in d4.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        ct_ls2.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass


fda_ls = []     #list to hold the fda RSS links
fda_ls2 = []
fda_ls3 = []

#FDA drugs
d5 = feedparser.parse('https://www.fda.gov/AboutFDA/ContactFDA/StayInformed/RSSFeeds/Drugs/rss.xml')
for post in d5.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        fda_ls.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass
    
#FDA press releases
d6 = feedparser.parse('https://www.fda.gov/AboutFDA/ContactFDA/StayInformed/RSSFeeds/PressReleases/rss.xml')
for post in d6.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        fda_ls2.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass
    
#FDA vaccines and biologics
d7 = feedparser.parse('https://www.fda.gov/AboutFDA/ContactFDA/StayInformed/RSSFeeds/Biologics/rss.xml')
for post in d7.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        fda_ls3.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

emea_ls = []     #list to hold the emea RSS links
emea_ls2 = []
emea_ls3 = []
emea_ls4 = []
#EMA Human medicines: pending European commission decisions and European public assessment reports (EPARs)
d8 = feedparser.parse('http://www.ema.europa.eu/ema/pages/rss/epar_human.xml')
for post in d8.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        emea_ls.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

    
#EMA New medicines: human and veterinary
d9 = feedparser.parse('http://www.ema.europa.eu/ema/pages/rss/new_medicines.xml')
for post in d9.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        emea_ls2.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

    
#EMA News and press releases - contains all committees' news like CHMP
d10 = feedparser.parse('http://www.ema.europa.eu/ema/pages/rss/news.xml')
for post in d10.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except: 
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        emea_ls3.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass


#EMA What's new
d11 = feedparser.parse('http://www.ema.europa.eu/ema/pages/rss/whats_new.xml')
for post in d11.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        emea_ls4.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass


pmda_ls = []
#PMDA.go.jp What's new
d12 = feedparser.parse('https://www.pmda.go.jp/rss_008.xml')
for post in d12.entries:
    pub_date = post.updated[:10].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        pmda_ls.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass


#PRNewsWire Health
d13 = feedparser.parse('http://www.prnewswire.com/rss/health/all-health-news.rss')
for post in d13.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        prnw_ls4.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

eu_ct_ls=[]
#european clinical trial empty search query
d14=feedparser.parse('https://www.clinicaltrialsregister.eu/ctr-search/rest/feed/bydates?query=')
for post in d14.entries:
    try:
        pub_date = post.published[:16].rstrip()
        pub_title = post.title
        #try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        eu_ct_ls.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass


#google news from Jon K. <--- who is Jon K.    
google_news_Jon_ls=[]
jons_drugs = ['Aubagio', 'Teriflunomide', 'Mirabegron', 'Solabegron', 'ARGX-113', 'UCB7665', 'Telotristat', 'Encorafenib', \
              'Ulixertinib', 'Mavrilumab', 'GDC-0853', 'PRN1008', 'GS-4059', 'BMS-986142', 'LY3337641']
jons_companies = ['Argen-x', 'Momenta', 'Syntimmune', 'UCB', 'Lexicon Pharmaceuticals', 'Astellas', 'GTX Inc.', \
                  'Viking Therapeutics', 'Immunic', 'Array Biopharma', 'Mustang Bio', 'Foundation Medicine', 'Loxo', \
                  'Ignyta', 'Odonate Therpeutics', 'Springworks', 'Bridgebio', 'Bioness', 'BlueWind', 'Axonics', \
                  'Valencia Technologies']
jons_diseases = ["Pulmonary Arterial Hypertension", "Mutliple Sclerosis", "Inflammatory Bowel Disease", "Rheumatoid Arthritis", \
                 "Ulcerative Colitis", "Crohn's Disease", "Systemic Lupus Erythematous", "Lupus Nephritis", "Atopic Dermatitis",\
                 "Psoriasis", "Psoriatic arthritis", "Ankylosing Spondylitis", "Organ Transplant Rejection", \
                 "Giant Cell Arteritis", "ANCA Vasculitis", "Uveitis", "Hidradenitis Suppurativa",\
                 "Juvenile Idiopathic Arthritis", "Primary Sclerosis Cholangitis", "Vitiligo", \
                 "Idiopathic Thrombocytopenic Purpura", "Graves Disease", "Myasthenia Gravis", \
                 "Neuromyelitis Optica", "Pemphigus", "Bullous Pemphigoid", "Celiac", "Scleroderma", \
                 "Systemic Sclerosis", "Sjogren's Syndrome", "Asthma", "Peanut Allergy", "V600 colorectal cancer", \
                 "V600 metastatic melanoma", "K-RAS NSCLC", "Pediatric low-grade glioma", "Stress Urinary incontinence", \
                 "Urge urinary incontinence", "Overactive bladder"]
jons_targets = ["Tryptophan Hydroxylase","TPH1", "Purinoceptor P2X3", "Purinergic Receptor P2X3", "P2X3", "P2RX3", \
                "Beta-adrenergic receptor", "Beta3", "B3", "B3-AR", "ADRB3", "Selective androgen receptor modulator",\
                "SARM", "Bruton's Tyrosine Kinase", "BTK", "Dihydroorotate Dehydrogenase", "DHODH", \
                "Granulocyte-macrophage colony-stimulating factor", "GM-CSF", "Tyrosine kinase 2", "TYK2", \
                "Lysophosphatidic acid receptor 1", "LPA1", "Purinoceptor P2X7", "Purinergic Receptor P2X7", \
                "P2X7", "P2RX7", "Interleukin-18", "IL18", "Src homology region 2 domain-containing phosphatase-1", \
                "SHP1", "Sphingosine-1-phosphate receptor 1", "S1P1", "interleukin-1 receptor-associated kinase 4", \
                "IRAK4", "Interleukin-17", "IL-17", "Interleukin-23", "IL-23", "CD40", "BRAF", "RAF", "MEK", \
                "Extracellular- regulated Kinase", "ERK", "Interleukin-6", "IL-6", "Janus Kinase", "JAK", \
                "Complement 5a", "C5a", "NLR Family Pyrin Domain Containing 3", "NLRP3", "CIAS1", \
                "RAR-related orphan receptor gamma", "ROR gamma", "ROR-GT", "RORC", "RORγ",\
                "Neonatal Fc receptor", "FcRn", "Spleen tyrosine kinase", "Syk", "Interleukin-8", "IL-8", \
                "Interleukin-33", "IL-33", "Interferon-alpha", "IFN-alpha", "Blood-Dendritic-Cell-Antigen-2", \
                "BDCA", "CD303", "Toll-like receptor 7", "TLR7", "Peptidylarginine Deiminase", "PAD", \
                "Protein Arginine Deaminase", "Interleukin-21", "IL-21", "Intravenous immunoglobulin", "IVIG",\
                "Interleukin-2", "IL-2", "Neurokinin 1", "NK-1", "Tacyhkinin 1", "TACR1", "Neurokinin 3", "NK-3", \
                "Tacyhkinin 3", "TACR3", "Neurokinin B", "Prostaglandin DP2 receptor", "prostaglandin D2", \
                "Chemoattractant receptor-homologous molecule expressed on TH2 cells", "CRTH2", "DP2", \
                "Cyclin dependent kinase 4-6", "CDK4-6", "CD38", "Interleukin-2–inducible kinase", "ITK",\
                "Nerve growth factor", "NGF", "Histamine 4", "Histamine H4 receptor", "H4", \
                "protein-tyrosine phosphatase 2C", "protein-tyrosine phosphatase 1D", "PTPN11", "SHP2", "PTP-1D",\
                "HDAC6", "Mitogen-activated protein kinase", "MAPK", "BRAF fusion", "P38"]
jons_other = ["Autophagy", "Autoantibody-mediated", "Pathogenic IgG", "Pathogenic autoantibody", "Paradoxical activation",\
              "B-cell mediated", "Oral taxane", "ERK re-activation", "BRAF fusion"]


jons_keywords = jons_drugs + jons_companies + jons_diseases + jons_targets + jons_other

    
#fiercepharma
fiercepharma_ls = []    #list to hold the fiercepharma RSS links

data_fiercepharma = feedparser.parse('https://www.fiercepharma.com/rss/xml') 
for post in data_fiercepharma.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        fiercepharma_ls.append(post.link) 
        repeated_rss_titles_check.append(pub_title)
    else:
        pass
    
#fiercebiotech
fiercebiotech_ls = []    #list to hold the fiercebiotech RSS links

data_fiercebiotech = feedparser.parse('https://www.fiercebiotech.com/rss/xml') 
for post in data_fiercebiotech.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        fiercebiotech_ls.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass


politco_morning_ehealth_ls = []
data_politico = feedparser.parse("https://www.politico.com/rss/morningehealth.xml")
for post in data_politico.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        politco_morning_ehealth_ls.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

        

google_pharma = []
data_google_pharma = feedparser.parse("https://www.google.com/alerts/feeds/06134438513215293937/2756707124756402355")
for i, post in enumerate(data_google_pharma.entries):
    pub_date = post.published[:10].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        google_pharma.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass


seekingalpha_healthcare = []

data_seekingalpha = feedparser.parse("https://seekingalpha.com/news/healthcare/feed")
for post in data_seekingalpha.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        seekingalpha_healthcare.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

##Nature RSS Feed
nature_current = []
data_naturecurrent = feedparser.parse("http://feeds.nature.com/nature/rss/current") 
for post in data_naturecurrent.entries:
    pub_date = post.updated
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        nature_current.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

## Cell RSS Feeds 
        
cell_cell = []
data_cell_cell = feedparser.parse("https://www.cell.com/cell/current.rss")
for post in data_cell_cell.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title 
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_cell.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

cell_cancer = [] 

data_cell_cancer = feedparser.parse("https://www.cell.com/cancer-cell/current.rss")
for post in data_cell_cancer.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_cancer.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

cell_chembio = []
data_cell_chembio = feedparser.parse("https://www.cell.com/cell-chemical-biology/current.rss")
for post in data_cell_chembio.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title 
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_chembio.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

cell_host = []
data_cell_host = feedparser.parse("https://www.cell.com/cell-host-microbe/current.rss")
for post in data_cell_host.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title 
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_host.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

cell_metabolism = []
data_cell_metabolism = feedparser.parse("https://www.cell.com/cell-metabolism/current.rss")
for post in data_cell_metabolism.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_metabolism.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

cell_reports = []
data_cell_reports = feedparser.parse("https://www.cell.com/cell-reports/current.rss")
for post in data_cell_reports.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title 
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_reports.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass
    
cell_stem = []
data_cell_stem = feedparser.parse("https://www.cell.com/cell-stem-cell/current.rss")
for post in data_cell_stem.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_stem.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

cell_system = []
data_cell_system = feedparser.parse("https://www.cell.com/cell-systems/current.rss")
for post in data_cell_system.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title 
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_system.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

cell_currbio = []
data_cell_currbio = feedparser.parse("https://www.cell.com/current-biology/current.rss")
for post in data_cell_currbio.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_currbio.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

cell_devcell = []
data_cell_devcell = feedparser.parse("https://www.cell.com/developmental-cell/current.rss")
for post in data_cell_devcell.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_devcell.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass
    
cell_immunity = []
data_cell_immunity = feedparser.parse("https://www.cell.com/immunity/current.rss")
for post in data_cell_immunity.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_immunity.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

cell_molecell = []
data_molecell = feedparser.parse("https://www.cell.com/molecular-cell/current.rss")
for post in data_molecell.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_molecell.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

cellneuron = []
data_cellneuron = feedparser.parse("https://www.cell.com/neuron/current.rss")
for post in data_molecell.entries:
    pub_date = post.prism_publicationdate
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        cell_molecell.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

## Lancet RSS feeds 
lancet_clinmed = []
data_lancet_clinmed = feedparser.parse("https://www.thelancet.com/rssfeed/eclinm_current.xml")
for post in data_lancet_clinmed.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_clinmed.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

lancet = []
data_lancet = feedparser.parse("https://www.thelancet.com/rssfeed/lancet_current.xml")
for post in data_lancet.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try: 
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

lancet_child = []
data_lancet_child = feedparser.parse("https://www.thelancet.com/rssfeed/lanchi_current.xml")
for post in data_lancet_child.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title 
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except: 
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_child.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

lancet_diabetes = []
data_lancet_diabetes = feedparser.parse("https://www.thelancet.com/rssfeed/landia_current.xml")
for post in data_lancet_diabetes.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_diabetes.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass
 
lancet_gast = []
data_lancet_gast = feedparser.parse("https://www.thelancet.com/rssfeed/landia_current.xml")
for post in data_lancet_gast.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_gast.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

lancet_hema = []
data_lancet_hema = feedparser.parse("https://www.thelancet.com/rssfeed/lanhae_current.xml")
for post in data_lancet_hema.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_hema.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

lancet_hiv = []
data_lancet_hiv = feedparser.parse("https://www.thelancet.com/rssfeed/lanhae_current.xml")
for post in data_lancet_hiv.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_hiv.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

lancet_infdis = []
data_lancet_infdis = feedparser.parse("https://www.thelancet.com/rssfeed/laninf_current.xml")
for post in data_lancet_infdis.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_infdis.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

lancet_neuro = [] 
data_lancet_neuro = feedparser.parse("https://www.thelancet.com/rssfeed/laneur_current.xml")
for post in data_lancet_neuro.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_neuro.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass
    
lancet_onc = []
data_lancet_onc = feedparser.parse("https://www.thelancet.com/rssfeed/lanonc_current.xml")
for post in data_lancet_onc.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_onc.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

lancet_pub = []
data_lancet_pub = feedparser.parse("https://www.thelancet.com/rssfeed/lanpub_current.xml")
for post in data_lancet_pub.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_pub.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

lancet_res = []
data_lancet_res = feedparser.parse("https://www.thelancet.com/rssfeed/lanpub_current.xml")
for post in data_lancet_res.entries:
    pub_date = post.prism_publicationdate[:10]
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        lancet_res.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

##Adding ICER RSS Feed
ICER = []
data_ICER = feedparser.parse("https://icer-review.org/feed/")
for post in data_ICER.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        ICER.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

#Express Scripts
exprs_scrpt = []
data_exprs_scrpt = feedparser.parse("https://lab.express-scripts.com/rss")
for post in data_exprs_scrpt.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        exprs_scrpt.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

#BusinessWire
businesswire = []
data_bsnwire = feedparser.parse("https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeEVlZWA==")
for post in data_bsnwire.entries:
    pub_date = post.published[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        businesswire.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

##Medrxiv 
medrxiv = []
data_medrxiv = feedparser.parse("http://connect.medrxiv.org/medrxiv_xml.php?subject=all")
for post in data_medrxiv.entries:
    pub_date = post.date[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        medrxiv.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass

biorxiv = []
data_biorxiv = feedparser.parse("http://connect.biorxiv.org/biorxiv_xml.php?subject=all")
for post in data_biorxiv.entries:
    pub_date = post.prism_publicationdate[:16].rstrip()
    pub_title = post.title
    try:
        pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        pub_date_fmt = 'no_date'
    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
        biorxiv.append(post.link)
        repeated_rss_titles_check.append(pub_title)
    else:
        pass
    
###############################################################################
##Incorporating new RSS links from wishlist
q_path = path #adjust to necessary path
q = pd.read_csv(q_path + 'OSS_document_sources.csv')

q_source = q['RSS_source']
q_link = q['RSS_link']

nest_dict = {}
rss_dict = {source:link for source, link in zip(q_source, q_link)}

regex =r"([0-9]{4}-[0-9]{2}-[0-9]{2})"
publi_regex = r"(publi[shed|cation])"
useless_links = []
func_rss_feeds = []

for key, value in rss_dict.items():
    data_link = feedparser.parse(value)
    
    data_list = []
    
    for post in data_link.entries:
    
        if len(post) > 0:
            func_rss_feeds.append(value)
        
        if 'published' in post.keys():
            try:
                pub_date = post.published[:16].rstrip()
                pub_title = post.title
                pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
                if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
                    data_list.append(post.link)
                    repeated_rss_titles_check.append(pub_title)
            
            except:
                try:
                    pub_date = re.search(regex, post.published).group()
                    pub_title = post.title
                    pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
                    if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
                        data_list.append(post.link)
                        repeated_rss_titles_check.append(pub_title)
                    else:
                        pass
                
                except:
                    
                    try:
                        pub_date = post.published[:7]
                        pub_title = post.title
                        try:
                            pub_date_fmt = datetime.strptime(pub_date, '%Y%m%d').strftime('%d %b %Y')
                        except:
                            pub_date_fmt = 'no_date'
                        if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
                            data_list.append(post.link)
                            repeated_rss_titles_check.append(pub_title)
                        else: 
                            pass
                    
                    except:
                        if len(post.published) <= 1:
                            useless_links.append(value)
                            Exception('post is {}'.format(post.published))
        elif 'prism_publicationdate' in post.keys():
            try:
                pub_date = post.prism_publicationdate
                pub_title = post.title
                pub_date_fmt = datetime.strptime(pub_date, '%Y-%m-%d').strftime('%d %b %Y')
                if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
                    data_list.append(post.link)
                    repeated_rss_titles_check.append(pub_title)
            except: 
                1+1
        elif len(re.findall(publi_regex, str(post.keys()))) == 0:
            useless_links.append(value)
        
        else:
            continue
    
    nest_dict[value] = data_list    


for key, value in nest_dict.items():
    if len(nest_dict[key]) == 0:
        useless_links.append(key)

def dict_cleaning(dict1, key_list):
    dict_copy = dict1.copy()
    for key in key_list:
        del dict_copy[key]
    return dict_copy
        
def unique_links(list1):
    unique_list = []   
    for i in list1:
        if i not in unique_list:
            unique_list.append(i)
    return unique_list


useless_links = unique_links(useless_links)
cln_links = dict_cleaning(nest_dict, useless_links)                 
unique_func_rss = unique_links(func_rss_feeds)

""" Create a map of RSS source to RSS link to RSS produced links for creating
lists later"""


q_ref = q[['RSS_source','RSS_link']]
cln_rss = cln_links.keys()
cols_to_add = []

unique_func_rss = pd.DataFrame(unique_func_rss).rename(columns = {0:'RSS_link'})
all_func_rss = pd.merge(q_ref, unique_func_rss, on = 'RSS_link', how = 'right')
chkd_rss_src = q_ref[q_ref['RSS_link'].isin(cln_rss)] 

#save Functional and nonfunctional RSS Sources separately for reference in EC2 instance
all_func_rss.to_csv(path + 'Functional_RSS_Sources.csv')
useless_links_df = pd.DataFrame(useless_links)
useless_links_df.to_csv(path + 'Non_Functional_RSS_Sources.csv')

##############################################################################3

#create an array to hold the lists of RRS links
new_rss_source_range = range(0, len(chkd_rss_src) + 1)
A_row_count = 16 + len(jons_keywords) + 5 + len(new_rss_source_range) + 150 #<--- add new links change array here

A=np.empty((A_row_count,2),dtype=object) #creates an array of object
A.fill([])  #change object type to list

#create an array to hold the lists of new RSS links
A_new=np.empty((A_row_count,col+5),dtype=object) #creates an array of object
A_new.fill([])  #change object type to list

A_summary=np.empty((len(data)+1,col*2),dtype=object) #creates an array of object
A_summary.fill([])  #change object type to list

#google news section
google_news_Jon_ls = []
title_list = []

for i, keyword in enumerate(jons_keywords):
    A[16+i][0] = keyword + "_google_news_search"
    keyword_fmt = '"'+keyword+'"'
    params_solr = {'q': keyword_fmt.encode('utf8')}                                               
    params_solr = urlencode(params_solr)
    url = 'https://news.google.com/news/rss/search?' + params_solr + '&hl=en&gl=US&ned=us'
    d15=feedparser.parse(url)
    google_news_Jon_ls_temp = []
    keyword_start_time = time.time()
    for post in d15.entries:
        try:
            pub_date = post.published[:16]
            pub_title = post.title
            pub_date_fmt = datetime.strptime(pub_date, '%a, %d %b %Y').strftime('%d %b %Y')
            if pub_date_fmt == currentdate and pub_title not in repeated_rss_titles_check:
                google_news_Jon_ls_temp.append(post.link)
                repeated_rss_titles_check.append(pub_title)
            else:
                pass
        except:
            1+1
    google_news_Jon_ls.append(google_news_Jon_ls_temp) # <--- append each list of each keyword to a giant, apropos google list
    keyword_end_time = time.time()
    time_duration = (keyword_end_time - keyword_start_time)/60
    print('{}'.format(keyword) + ' takes ' + '{}'.format(time_duration) + ' minutes')
######

A[0][0] = 'website / RSS category'
A[0][1] = 'RSS links'

A[1][0] = "PRNWs-Clinical_Trials&Medical_Discoveries"
A[2][0] = "PRNWs-medical_and_pharmaceutical"
A[3][0] = "PRNWs-pharmaceutical"
A[4][0] = "PRNWs-Health"
A[5][0] = "CT.gov-added_or_modified_studies"
A[6][0] = "CT.gov-first_received_studies"
A[7][0] = "FDA-drugs"
A[8][0] = "FDA-press_releases"
A[9][0] = "FDA-vaccines_and_biologics"
A[10][0] = "EMEA-Human_medicines_(EPARs)"
A[11][0] = "EMEA-New_medicines"
A[12][0] = "EMEA-News_and_press_releases"
A[13][0] = "EMEA-What_is_new"
A[14][0] = "PMDA-What_is_new"
A[15][0] = "EU_CT-empty_search"


"""Deduplicating links from across different keywords. Duplicate links can arise
during the same 15 minute interval of web-scrapping if keywords produce same links"""

google_range = range(0,len(jons_keywords))
dup_link_removal = {}
for i, keywords, google_news_ls, in zip(google_range, jons_keywords, google_news_Jon_ls):
    dup_link_removal[keywords] = google_news_ls

result = {}
for value in dup_link_removal.values():
    for i in set(value):
        result[i] = 1 + result.get(i,0)

urls_to_deduplicate = []
for key,value in result.items():
    if value > 1:
        urls_to_deduplicate.append(key)

swag_duplicate = urls_to_deduplicate.copy()

for i, keywords ,google_news_ls in zip(google_range, jons_keywords,google_news_Jon_ls):
    A[16+i][0] = 'Google_Search_{}'.format(keywords) 
    A[16+i][1] = google_news_ls

for link in urls_to_deduplicate:
    link_counter = 0
    for i in google_range:
        if link in A[16+i][1]:
            #print(link)
            link_counter += 1
            #print(link_counter)
            if link_counter >= 2:
                #print(link) - checking for duplicated url removal
                #print('_______________^That was the link to remove^_____________________')
                #print(A[16+i][1]) - checking for duplicated url removal
                #print('_______________^This is the original links list^_____________________')
                A[16+i][1].remove(link)
                #print(A[16+i][1]) - checking for duplicated url removal
                #print('_______________^This is the modified links list^_____________________')
            

"""Links are now deduplicated across all of the google news scrapes"""
    
A[16+len(jons_keywords)][0] = "fiercepharma" #<--- added at the end after google
A[17+len(jons_keywords)][0] = "fiercebiotech" #<--- added at the end after google and fiercepharma
A[18+len(jons_keywords)][0] = "politico morning eHealth"
A[19+len(jons_keywords)][0] = "google pharma added by Krithika"
A[20+len(jons_keywords)][0] = "seeking alpha healtcare added by Krithika"
A[21 + len(jons_keywords)][0] = 'Nature Feed'
A[22 + len(jons_keywords)][0] = 'Cell Feed'
A[23 + len(jons_keywords)][0] = 'Cell - Cancer Feed'
A[24 + len(jons_keywords)][0] = 'Cell - Chemical Biology Feed'
A[25 + len(jons_keywords)][0] = 'Cell - Host Feed'
A[26 + len(jons_keywords)][0] = 'Cell - Metabolism Feed'
A[27 + len(jons_keywords)][0] = 'Cell - Reports'
A[28 + len(jons_keywords)][0] = 'Cell - Stem Cells'
A[30 + len(jons_keywords)][0] = 'Cell - System'
A[31 + len(jons_keywords)][0] = 'Cell - Current Biology'
A[32 + len(jons_keywords)][0] = 'Cell - Development Biology'
A[33 + len(jons_keywords)][0] = 'Cell - Immunity'
A[34 + len(jons_keywords)][0] = 'Cell - Molecular Cell'
A[35 + len(jons_keywords)][0] = 'Cell - Neuron'
A[36 + len(jons_keywords)][0] = 'Lancet - Clinical Medicine'
A[37 + len(jons_keywords)][0] = 'Lancet'
A[38 + len(jons_keywords)][0] = 'Lancet - Child and Adolescent Health'
A[39 + len(jons_keywords)][0] = 'Lancet - Diabetes and Endocrinology'
A[40 + len(jons_keywords)][0] = 'Lancet -  Gastroentology and Heptology'
A[41 + len(jons_keywords)][0] = 'Lancet - Haemtology'
A[42 + len(jons_keywords)][0] = 'Lancet - HIV'
A[43 + len(jons_keywords)][0] = 'Lancet - Infectious Diseases'
A[44 + len(jons_keywords)][0] = 'Lancet - Neurology'
A[45 + len(jons_keywords)][0] = 'Lancet - Oncology'
A[46 + len(jons_keywords)][0] =' Lancet - Respiratory' 
A[47 + len(jons_keywords)][0] = 'Lancet - Public Health'
A[48 + len(jons_keywords)][0] = 'ICER'
A[49 + len(jons_keywords)][0] = 'Express Scripts'
A[50 + len(jons_keywords)][0] = 'BusinessWire'
A[51 + len(jons_keywords)][0] = 'MedRXiv'
A[52 + len(jons_keywords)][0] = 'BioRXiv'
#Adding new RSS Sources to the A frame for labeling
rss_source_range = range(0, len(q_ref) + 1)
for i, rss_source in zip(rss_source_range, chkd_rss_src['RSS_source']):
    A[52 + len(jons_keywords) + i][0] = "{}".format(rss_source)


A[1][1] = prnw_ls 
A[2][1] = prnw_ls2
A[3][1] = prnw_ls3
A[4][1] = prnw_ls4
A[5][1] = ct_ls
A[6][1] = ct_ls2
A[7][1] = fda_ls
A[8][1] = fda_ls2
A[9][1] = fda_ls3
A[10][1] = emea_ls
A[11][1] = emea_ls2
A[12][1] = emea_ls3
A[13][1] = emea_ls4
A[14][1] = pmda_ls
A[15][1] = eu_ct_ls


A[16+len(jons_keywords)][1] = fiercepharma_ls
A[17+len(jons_keywords)][1] = fiercebiotech_ls
A[18+len(jons_keywords)][1] = politco_morning_ehealth_ls
A[19+len(jons_keywords)][1] = google_pharma
A[20+len(jons_keywords)][1] = seekingalpha_healthcare
A[21 + len(jons_keywords)][1] = nature_current
A[22 + len(jons_keywords)][1] = cell_cell
A[23 + len(jons_keywords)][1] = cell_cancer
A[24 + len(jons_keywords)][1] = cell_chembio
A[25 + len(jons_keywords)][1] = cell_host
A[26 + len(jons_keywords)][1] = cell_metabolism
A[27 + len(jons_keywords)][1] = cell_reports
A[28 + len(jons_keywords)][1] = cell_stem
A[30 + len(jons_keywords)][1] = cell_system
A[31 + len(jons_keywords)][1] = cell_currbio
A[32 + len(jons_keywords)][1] = cell_devcell
A[33 + len(jons_keywords)][1] = cell_immunity
A[34 + len(jons_keywords)][1] = cell_molecell
A[35 + len(jons_keywords)][1] = cellneuron
A[36 + len(jons_keywords)][1] = lancet_clinmed
A[37 + len(jons_keywords)][1] = lancet
A[38 + len(jons_keywords)][1] = lancet_child
A[39 + len(jons_keywords)][1] = lancet_diabetes
A[40 + len(jons_keywords)][1] = lancet_gast
A[41 + len(jons_keywords)][1] = lancet_hema
A[42 + len(jons_keywords)][1] = lancet_hiv
A[43 + len(jons_keywords)][1] = lancet_infdis
A[44 + len(jons_keywords)][1] = lancet_neuro
A[45 + len(jons_keywords)][1] = lancet_onc
A[46 + len(jons_keywords)][1] = lancet_res
A[47 + len(jons_keywords)][1] = lancet_pub
A[48 + len(jons_keywords)][1] = ICER
A[49 + len(jons_keywords)][1] = exprs_scrpt
A[50 + len(jons_keywords)][1] = businesswire
A[51 + len(jons_keywords)][1] = medrxiv
A[52 + len(jons_keywords)][1] = biorxiv



#Adding new RSS links from new RSS Sources to the A frame
for i, rss_link in zip(new_rss_source_range, chkd_rss_src['RSS_link']):
    A[52 + len(jons_keywords) + i][1] = cln_links[rss_link]


def update_SQL_through_flask(df, sql_ip):
    """
    This function updates the SQL DB which tracks the source url for redirecting
    input:
            - df: a dataframe with the data to be saved in SQL
            - sql_ip: the ip_address of the SQL DB ("10.71.0.111")
    output: none
    """
    
    for i, row in df.iterrows():
#        break
        solr_id = row['solr_id'].replace(' ', '%20')
        
        web_url = row['web_url'].replace("'",'').replace(';', '').replace('"','')
        redirect_url = web_url.replace(':', '**').replace('/', '!!')
        
        flask_url = 'http://' + sql_ip + '/link/' + solr_id + '/' + redirect_url #old server

        try:
            html_PR = get_html(flask_url)
        except Exception:
            print('was not able to access the url ',flask_url,' to save as an html file')
            1+1    
        
    print('succesful update of SQL DB: ', sql_ip)       






def update_SQL(df, sql_ip):
    """
    This function updates the SQL DB which tracks the source url for redirecting
    input:
            - df: a dataframe with the data to be saved in SQL
            - sql_ip: the ip_address of the SQL DB ("10.71.0.111")
    output: none
    """
    '''
    get the current version of the SQL table
    '''
    conn = MySQLdb.connect(host= sql_ip,
                      user="roivant",
                      passwd="Roivant1", 
                      db="ome_alert_public")
    
    cur = conn.cursor()
    
    sqlstring1 = """SELECT * FROM ome_alert_public.solr_docid_url;""" 
                
                
    cur.execute(sqlstring1)
    colnames = [desc[0] for desc in cur.description]
    df_raw = cur.fetchall()
    df_mysql = DataFrame(data = list(df_raw), columns = colnames)
    
    conn.close()
    df_mysql.index+=1
    del df_raw
    
    #get the highest id
    max_id = df_mysql['idsolr_docid_url'].max()
    
    '''
    Upadate the SQL table with the new data
    '''
    conn = MySQLdb.connect(host= sql_ip,
                      user="roivant",
                      passwd="Roivant1", 
                      db="ome_alert_public")
    
    cur = conn.cursor()
    
    for i, row in df.iterrows():
        max_id += 1
        sql_string = '''INSERT INTO `ome_alert_public`.`solr_docid_url` (`idsolr_docid_url`, `solr_id`, `web_url`, `scraping_date`) VALUES (%s, "%s", "%s", "%s");'''
        web_url = row['web_url'].replace("'",'').replace(';', '').replace('"','')
        try:
            cur.execute(sql_string%(max_id, row['solr_id'], web_url, row['scraping_date']))
        except Exception as e:
            print('error updating SQL table with PR url link: ', e)
            cur.execute(sql_string%(max_id, row['solr_id'], 'NA', row['scraping_date']))
    
    conn.commit()
    conn.close() 
    
 
my_file = Path(path + "RSS_ref.csv")

if my_file.is_file():   #checks if a reference file exists   
    with open(path + 'RSS_new.csv', 'w', encoding='utf-8-sig') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
        for row in A:
            thedatawriter.writerow(row)
            
    #re-open reference data file and read it as a csv file
    f = open(path + "RSS_new.csv", encoding='utf-8-sig')
    csv_f = csv.reader(f)
    #initialize a blank list
    data = []
    #append each row of the csv file to the list data
    for row in csv_f:
        data.append(row)
    #save the headers to Header and remove them for the list    
    Header = data[0]
    data.pop(0) 
       
    #open reference data file and read it as a csv file
    f = open(path + "RSS_ref.csv", encoding='utf-8-sig')
    csv_f = csv.reader(f)
    #initialize a blank list
    data_ref = []
    #append each row of the csv file to the list data
    for row in csv_f:
        data_ref.append(row)
    #save the headers to Header and remove them for the list    
    Header_ref = data_ref[0]
    data_ref.pop(0)
    
    #backup current ref file since it will be overwritten
    with open(path + 'RSS_ref_old.csv', 'w', encoding='utf-8-sig') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
        thedatawriter.writerow(Header_ref)
        for row in data_ref:
            thedatawriter.writerow(row)
            
    #save new file as ref file for next execution
    with open(path + 'RSS_ref.csv', 'w', encoding='utf-8-sig') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
        thedatawriter.writerow(Header)
        for row in data:
            thedatawriter.writerow(row)
            
    
    
    #identify new links by comparing new to ref and move only new links to A_new
    data_df_new = pd.DataFrame(data, columns  = ['RSS_Source','Links'])
    data_df_new['Links'] = data_df_new['Links'].apply(lambda x: ast.literal_eval(x))
    data_df_new.to_csv(path + 'new_data.csv')
    data_df_ref = pd.DataFrame(data_ref, columns = ['RSS_Source','Links'])
    data_df_ref['Links'] = data_df_ref['Links'].apply(lambda x: ast.literal_eval(x))
    data_df_ref.to_csv(path + 'ref_data.csv')
    
    
    
    sc = pd.DataFrame(columns = ['RSS_Source','Links'])
    source_new_dict = {}
    repeated_links_check = []
    counter = 0 
    for row, source in enumerate(data_df_new['RSS_Source']):
       new = data_df_new.loc[data_df_new['RSS_Source'] == source].reset_index()['Links'][0]
       #print(new)
       try:
           ref_comp = data_df_ref.loc[data_df_ref['RSS_Source'] == source].reset_index()['Links'][0]
           
           #print(ref_comp)
           only_new = [x for x in new if x not in ref_comp]
       except:
           only_new = new
       source_new_dict[source] = only_new
    
    #create dataframe for formatting into A_new
    sc['RSS_Source'] = source_new_dict.keys()
    sc['Links'] = source_new_dict.values()
    
    #deduplicate links within the same 15 minute span from across all currently scraped sources
    intra_15_dedup = []
    for i in sc['Links']:
        for x in i:
            intra_15_dedup.append(x)
            
    duplicates = {}      
    link_counts = Counter(intra_15_dedup)
    for k,v in link_counts.items():
        if v > 1:
            duplicates[k] = v
    

    for k, v in duplicates.items():
        counter = 0
        for i in sc['Links']:
            if k in i:
                counter += 1
                if counter > 1:
                    while k in i: i.remove(k)
                else:
                    pass


    #Create A_new in format necessary for get_PR function
    for i,row in sc.iterrows():
        A_new[i][0] = row['RSS_Source']
        
        for j,link in enumerate(row['Links']):
            A_new[i][1+j] = link    
        
#    for k, row in enumerate(A_new):
#       get_PR(A_new, row, f, k, col, 'RSS', A_FL)
    
    
    #save the list of new RSS to a csv file        
    with open(path + 'new_RSS_links.csv', 'w', encoding='utf-8') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
        for row in A_new:
            if len(row[1])>0:
                thedatawriter.writerow(row)
                
                
    '''
    This part of the code handles SQL table update for PR source url tracking
    '''
    #satck A into a data frame
    df_ls = []
    for row_idx, row in enumerate(A_new):
        if len(row[1])>0:
            date_PR = datetime.now().strftime("%d-%m-%Y") #French format...
            for link_idx in range(103):
                if len(row[1 + link_idx])>0:
                    solr_id = row[0] + '_PR' + str(link_idx) + '_' + date
                    
                    web_url = row[1 + link_idx]
                    if web_url.startswith('/'):
                        if web_url.startswith('//'):
                            url = 'http://' + web_url.lstrip('//')
                        else: #there was a bug here @V2.0 - YMR
                            root_path = get_root_path(row[1],0) #there was a bug here @V2.0 - YMR
                            url = root_path + web_url #there was a bug here @V2.0 - YMR
                    else:
                        if web_url.startswith('./'):
                            root_path = get_root_path(row[1], 1)
                            url = root_path + web_url.lstrip('.')
                        else:
                            url = web_url
                    
                    df_ls.append([solr_id, url, timestamp])
            
    columns = ['solr_id', 'web_url', 'scraping_date']
    df = pd.DataFrame.from_records(df_ls, columns=columns)
    
    
    #update the SQL DB
    #SQL DB on old AWS server
    #try:
    #    update_SQL(df, "10.71.0.111")   
    #except Exception as e:
    #    print('error updating the old AWS server SQL DB: ', e)      
        
    #SQL DB on new AWS server
    try:
        print('SQL upload to new server - start')
        update_SQL_through_flask(df, "52.23.161.54")
        print('SQL upload to new server - end') 
    except Exception as e:
        print('error updating the new AWS server SQL DB: ', e)     

            
    total_links = {}     

#    print("___________________________\n")
#    for i, item in enumerate(A_new):
#        #print(item[0])
#        #total_links[item[0]] += 1
#        if(len(item[1]) > 0):
#            print(str(i) + ": " + str(item))
#
#    print("\n___________________________")
##    
        
    #write PR summary to a text file
    with open(path + 'new_RSS_summary.txt', 'w', encoding='utf-8') as f:
        #k=0
        #r=0 #failed PR access iteration variable
        #for k, row in enumerate(A):
        #    get_PR(A, row, f, k, col)
        """print("printing A_new")
                                for row in A_new:
                                    print(row[1])"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        #for k, row in enumerate(A_new):
           # get_PR(A_new, row, f, k, col, 'RSS')
            # Start the load operations and mark each future with its URL
            future_to_url = {executor.submit(get_PR, A_new, row, f, k, col, 'RSS', A_FL): row for k, row in enumerate(A_new)} #get_PR(A, row, f, k, col)
            for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
                url = future_to_url[future]
                #print(str(i) + ": " + str(future))

            #for news, number in total:
                #print(news, ": ", str(number))
            #for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
                #url = future_to_url[future]
                #print(i)
else:
    with open(path + 'RSS_ref.csv', 'w', encoding='utf-8-sig') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
        for row in A:
            thedatawriter.writerow(row)

with open(path + 'new_RSS_summary2.txt', 'w', encoding='utf-8') as f:
    for row in A_summary:
        if len(row[0])>0:
            f.write('\n')
            f.write('\n')
        for col2 in row:
            try:
                if col2.startswith("http:"):
                    f.write('\n')
                f.write(col2)
                f.write('\n')
            except Exception:
                1+1

with open(path + 'failed_links_RSS.csv', 'w', encoding = 'utf-8-sig') as mycsv:
    datawriter = csv.writer(mycsv, lineterminator = '\n')
    for row in A_FL:
        datawriter.writerow(row)
                
'''
this part of the code handles the file transfer from EC2_A to EC2_B calling a 
shell script for pdf and html files
'''

print('Moving pdf files to OSS EC2 instance')
pdf_string = '/root/PR_webscraping/move_pdf_195.sh ' + pdf_directory
subprocess.call(shlex.split(pdf_string))

#pdf_string = '/root/PR_webscraping/move_pdf_248.sh ' + pdf_directory
#subprocess.call(shlex.split(pdf_string))

#pdf_string = '/root/PR_webscraping/move_pdf_236.sh ' + pdf_directory
#subprocess.call(shlex.split(pdf_string))

#pdf_string = '/root/PR_webscraping/move_pdf_235.sh ' + pdf_directory
#subprocess.call(shlex.split(pdf_string))

pdf_string = '/root/PR_webscraping/move_pdf.sh ' + pdf_directory
subprocess.call(shlex.split(pdf_string))

print('Moving html files to OSS EC2 instance')
html_string = '/root/PR_webscraping/move_html_195.sh ' + html_directory
subprocess.call(shlex.split(html_string))

#html_string = '/root/PR_webscraping/move_html_248.sh ' + html_directory
#subprocess.call(shlex.split(html_string))

#html_string = '/root/PR_webscraping/move_html_236.sh ' + html_directory 
#subprocess.call(shlex.split(html_string))

#html_string = '/root/PR_webscraping/move_html_235.sh ' + html_directory
#subprocess.call(shlex.split(html_string))

html_string = '/root/PR_webscraping/move_html.sh ' + html_directory
subprocess.call(shlex.split(html_string))


print("--- %s seconds ---" % round(time.time() - start_time, 2))
print("\n\n CODE EXECUTION COMPLETED")
print(datetime.today().strftime("%Y-%m-%d::%H:%M"))


###############################################################################
"""Old Code for reference"""

###############################################################################
""" Function form below: """
#    def intra_15_dedup_func(dataframe_series):
#        intra_15_dedup = []
#        for i in dataframe_series:
#            for x in i:
#                intra_15_dedup.append(x)
#                
#        duplicates = {}      
#        link_counts = Counter(intra_15_dedup)
#        for k,v in link_counts.items():
#            if v > 1:
#                duplicates[k] = v
#        
#    
#        for k, v in duplicates.items():
#            counter = 0
#            for i in dataframe_series:
#                if k in i:
#                    counter += 1
#                    if counter > 1:
#                        while k in i: i.remove(k)
#                    else:
#                        pass
#        return dataframe_series
#    
    
"""Intra 15 minute deduplicated link check"""   
#    intra_15_dedup = []
#    for i in sc['Links']:
#        for x in i:
#            intra_15_dedup.append(x)
#            
#    duplicates = {}      
#    link_counts = Counter(intra_15_dedup)
#    for k,v in link_counts.items():
#        if v > 1:
#            duplicates[k] = v
#    
#    
    #check = pd.DataFrame(list(source_new_dict.items()), columns = ['RSS_Source','Links'])

        
"""Previous A_new formatting"""
#                
#    new_PR = []
#    l=0
#    counter = 0
#    for k, row in enumerate(data):    #data has the new RSS data
#        end = data_ref[k].count('')
#        for m in range(0,end):  #removes empty list elements to compare ref vs new
#            data_ref[k].remove('')
#        if row != data_ref[k]:
#            
#            #removes '[' and ']' from the row string to convert it back to a list
#            A_new[k+1][0]=row[0]    #RSS website
#            x=1
#            try :
#                #removes '[' and ']'
#                striped_data = row[x][1:(len(row[x])-1)]
#                striped_data_ref = data_ref[data.index(row)][x][1:(len(data_ref[data.index(row)][x])-1)]
#                #converts the string back to a list
#                data_list = striped_data.split(',')
#                #removes blank space and "'" from link name
#                for l,link in enumerate(data_list):
#                    data_list[l] = link.strip()
#                for l,link in enumerate(data_list):
#                    data_list[l] = link.strip("'")
#                data_ref_list = striped_data_ref.split(',')
#                for l,link in enumerate(data_ref_list):
#                    data_ref_list[l] = link.strip()
#                for l,link in enumerate(data_ref_list):
#                    data_ref_list[l] = link.strip("'")
#                set_data_ref = set(data_ref_list)   #creates a list with unique elements
#                #creates a list with elements unique to new PR data
#                if "https://clinicaltrials.gov/ct2/show/" in data_list[0] and "lup_s=" in data_list[0]: #ct.gov added or modified
#                    data_NCT_list = []
#                    for link in data_list:
#                        NCT_start = link.find('NCT', 0, len(link))
#                        NCT=link[NCT_start:NCT_start+11]
#                        data_NCT_list.append(NCT)
#                    data_ref_NCT_list = []
#                    for link in data_ref_list:
#                        NCT_start = link.find('NCT', 0, len(link))
#                        NCT=link[NCT_start:NCT_start+11]
#                        data_ref_NCT_list.append(NCT)
#                    set_data_ref_NCT = set(data_ref_NCT_list)   #creates a list with unique elements
#                    differences = [x for x in data_NCT_list if x not in set_data_ref_NCT]
#                    differences = set(differences)
#
#                    m=0
#                    for diff in differences:
#                        for l,link in enumerate(data_list):
#                            if diff in link:
#                                link = link.strip()
#                                link = link.strip('\'')
#                                A_new[k+1][1+m]=link    #saves only the new links that may be PR links
#                                print(m)
#                                m+=1
#                else:
#                    differences = [x for x in data_list if x not in set_data_ref]
#                    differences = set(differences)
#                    l=0
#                    for diff in differences:
#                        diff = diff.strip()
#                        diff = diff.strip('\'')
#                        A_new[k+1][1+l]=diff    #saves only the new links that may be PR links
#                        l+=1
#            except Exception:
#                1+1
#            if len(A_new[k+1][1])>0:
#                print('New RSS for website: ')
#                print(row[0])
#                print(A_new[k+1][1])
#
#            
#    
#    if l==0:
#        print('No new RSS found')
#
#    
