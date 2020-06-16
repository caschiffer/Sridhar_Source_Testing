# -*- coding: utf-8 -*-
"""
Created on Thu Feb  9 08:57:01 2017

@author: yoann.randriamihaja
v1.0: first EC2 implementation - YMR
v2.0: updates made by Krithika
v3.0: correction of bugs introduced in V2.0 - YMR
V4.0: added saving of PR source url to a SQL DB - YMR
V5.0: updated saving of PR source url to a SQL DB - YMR 
"""


#import csv library
import csv
import time
import numpy as np
import os
import socket
import feedparser
import subprocess
import shlex
import pandas as pd
import random
import urllib.request
from urllib.parse import unquote
import html5lib
import lxml
from google import google
from google.modules.utils import _get_search_url, get_html, get_pdf, get_pdf_summary
from google.modules.standard_search import _get_link
import re
from bs4 import BeautifulSoup
from random import randint
import concurrent.futures
from pathlib import Path
import urllib.parse
import datetime
import MySQLdb
from pandas import DataFrame 

timestamp = datetime.date.today().strftime("%Y-%m-%d")

pd.set_option("display.width", None)
start_time = time.clock()

#timeout in seconds
timeout=30
socket.setdefaulttimeout(timeout)
#path = "R:/Business Development/Computational Research/for Yoann/U_drive/Coding/Python/web-scrapping/google-news-search-Feb-17/EC2 version/"
path="/root/PR_webscraping/"
date = time.strftime("%d-%m-%Y")

#creates the daily directory to save the PR pdf when PR is not an html file
pdf_folder = "pdf/" + date + '/'
pdf_directory = os.path.dirname(path + pdf_folder)
if not os.path.exists(pdf_directory):
    os.makedirs(pdf_directory)
    
#creates the daily directory to save the PR html
html_folder = "PR_html_saving/" + date + '/'
html_directory = os.path.dirname(path + html_folder)
if not os.path.exists(html_directory):
    os.makedirs(html_directory)

#open data file and read it as a csv file
f = open( path + "phase3_ready_pharma_companies.csv", encoding = 'utf-8')
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

#function to check if a link has an email protection random number
#returns a flag number
def link_check(link):
    flag = 0
    if len(re.findall('email-protection', link))>0:
        flag = 1
    return flag


#returns a url root path to be merged with a relative path
def get_root_path(link, version):
    for i, c in enumerate(link):
        if version==0:
            if i > 6:   #ignore the first http://
                if link[i] == '/' and (link[i-4]=='.' or  link[i-3]=='.'):
                    root = link[:i]
                    return root
    if version==1:
        last_iter = 0
        for i, c in enumerate(link):
            if i > 6:   #ignore hte first http://
                if link[i] == '/' :
                    last_iter = i
        root = link[:last_iter]
        return root


#function to get the text summary from a new PR link
def get_PR_summary(url, proxies, path, html_name, version):
    try:
        #html_PR = get_html(url, proxy)
        html_PR = get_html(url)
    except Exception:
        print('was not able to access the url ',url,' to save as an html file')
        1+1            
    
    if html_PR:
        if b'PDF' in html_PR[:6]: #if it's a pdf, don't save it as an html
            return None
        #saves the html of the page to a text file
        with open(path + html_name,"wb") as file: #open file in binary mode
                 file.write(html_PR)
        #file.close()
        soup = BeautifulSoup(html_PR, "html.parser")
        
        summary ="" #initialize a string
        summary_cache = []
        if version == 'RSS':
            body_tag = soup.body
            for child in body_tag.descendants:
                print(child)
                if child.string and child.string != '\n' and child.string not in summary_cache:
                    #print(child.string)
                    summary = summary + child.string + "\n"
                    summary_cache.append(child.string)
            soup_text = soup.find_all('p')
            for i in range(0, len(soup_text)):
                if soup_text[i].text.strip() not in summary_cache:
                    summary = summary + soup_text[i].text.strip() + " "
                    summary_cache.append(soup_text[i].text.strip())
            return summary
            """
            divs = soup.find_all('div')
            for div in soup:
               # print(div.string)
                try:
                    if div.find(text=True) != '\n':
                        summary = summary + div.find(text=True)
                except Exception:
                    1+1
            """
        else:
            soup_text = soup.find_all('p')
            for i in range(0, len(soup_text)):
                summary = summary + soup_text[i].text.strip() + " "
        return summary
    else:
        return None

failed_list=[]
  
ik = 0
ii = 0

col=100 
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
def get_PR_link_cache(data, row, fail):

        time_start = time.clock()
        end = len(data)

        print('start caching PRESS RELEASES links')    
        j=0        
        url = row[2]    
        #if the company has no own PR website, then do a search on PRNewsWire.com
        if url == '':
            return None
            #url = url + row[0]
            #url = urllib.parse.quote_plus(url,'/:!#$%^&*()_-+=[]{}?', 'utf-8')            
        
        #html_res = get_html(url, proxy)
        html_res = get_html(url)               
        
        #each list of links can't have more than 32,000 characters to fit in an excell cell
        link_cache = []
        link_cache2 = []
        link_cache3 = []
        link_cache4 = []
        link_cache5 = []
        link_cache6 = []
        link_cache7 = []
        link_cache8 = []
        link_cache9 = []
        link_cache10 = []
        if not html_res:
            fail.append(url)
            print("no html results")
        #collects all the links within the web page
        if html_res:
            soup = BeautifulSoup(html_res, "html.parser")
            divs = soup.find_all('a')
            #check for website denying access while displaying an error page
            divs_flag = 0
            if len(divs) == 0:
                print("divs a href is empty!!")
                divs_flag=1
                time_end = time.clock()
                delta = time_end - time_start
                return None  #if return None, then the for loop needs to continue
    
            if divs_flag==1:    #if no links were found in the webpage, move to next company
                #ii = ii+1
                return None
            for a in divs:
                f = 0
                f_link_check = 0
                link = ''
                try:
                    if a["href"].startswith("http://"):
                        link = a["href"]
                        f_link_check = link_check(link)
                        f = 1
                    elif a["href"].startswith("./"):  
                        link = a["href"]
                        f_link_check = link_check(link)
                        f = 1            
                    elif a["href"].startswith("/"):
                        link = a["href"]
                        f_link_check = link_check(link)
                        f = 1            
                    elif a["href"].startswith("https://"):
                        link = a["href"]
                        f_link_check = link_check(link)
                        f = 1
                    elif a["href"].startswith("/url?"):
                        m = re.match('/url\?(url|q)=(.+?)&', link)
                        if m and len(m.groups()) == 2:
                            link = unquote(m.group(2))
                            f_link_check = link_check(link)
                            f = 1
                    else:
                        link = '/' + a["href"]
                        f_link_check = link_check(link)
                        f = 1       
                    #checks that the number of characters per list does not exceeds excel cell limit
                    if f == 1 and f_link_check==0:
                        if sum(len(i) for i in link_cache)<28000:
                            link_cache.append(link)
                        elif sum(len(i) for i in link_cache2)<28000:
                            link_cache2.append(link)
                        elif sum(len(i) for i in link_cache3)<28000:
                            link_cache3.append(link)
                        elif sum(len(i) for i in link_cache4)<28000:
                            link_cache4.append(link)
                        elif sum(len(i) for i in link_cache5)<28000:
                            link_cache5.append(link)
                        elif sum(len(i) for i in link_cache6)<28000:
                            link_cache6.append(link)
                        elif sum(len(i) for i in link_cache7)<28000:
                            link_cache7.append(link)
                        elif sum(len(i) for i in link_cache8)<28000:
                            link_cache8.append(link)
                        elif sum(len(i) for i in link_cache9)<28000:
                            link_cache9.append(link)
                        elif sum(len(i) for i in link_cache10)<28000:
                            link_cache10.append(link)
                except Exception as e:
                    print('no href found')
                                       
        
        if len(link_cache)!=0:            
            print('PR link cache found and saved')
            link_cache.sort()
            data[data.index(row)].append(link_cache)
        if len(link_cache2)!=0:
            link_cache2.sort()
            data[data.index(row)].append(link_cache2)
        if len(link_cache3)!=0:
            link_cache3.sort()
            data[data.index(row)].append(link_cache3)
        if len(link_cache4)!=0:
            link_cache4.sort()
            data[data.index(row)].append(link_cache4)
        if len(link_cache5)!=0:
            link_cache5.sort()
            data[data.index(row)].append(link_cache5)
        if len(link_cache6)!=0:
            link_cache6.sort()
            data[data.index(row)].append(link_cache6)
        if len(link_cache7)!=0:
            link_cache7.sort()
            data[data.index(row)].append(link_cache7)
        if len(link_cache8)!=0:
            link_cache8.sort()
            data[data.index(row)].append(link_cache8)
        if len(link_cache9)!=0:
            link_cache9.sort()
            data[data.index(row)].append(link_cache9)
        if len(link_cache10)!=0:
            link_cache10.sort()
            data[data.index(row)].append(link_cache10)
    
        #ii = ii +1
        #print(ii)
        #print(jj)
        time_end = time.clock()
        delta = time_end - time_start



fail = []

#data = data[:200]#for debug

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    # Start the load operations and mark each future with its URL
    future_to_url = {executor.submit(get_PR_link_cache, data, row, fail): row for row in data}
    for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
        #url = future_to_url[future]
        print(i)
        

A[0][0]='Company name'
A[0][1]='Company\'s PR website'
A_FL[0][0]='Company name and failed links'
for x in range(2, col):
    A[0][x]='New PR links'
"""
This part of the code will compare the new PR to the reference one (if any) for updates
It will generate a PR summary
"""

def get_PR(A, row, f, k, col, version):    #A is a table containning the new PR links
#row is a row of A, f is a text file, k is the iteration loop over A
#col is the maximum number of PR links
    
    summary_cache = []  #to check for summary duplicates coming from different url

    if version=='PR':
        start=2
    else:
        start=1
    if k>0: #skip the first row bc header

        for x in range(start, col):     #col is 100
            flag = False 
            if row[x]:
                if row[x].startswith('/'):
                    if row[x].startswith('//'):
                        url = 'http://' + row[x].lstrip('//')
                    else: #there was a bug here @V2.0 - YMR
                        root_path = get_root_path(row[1],0) #there was a bug here @V2.0 - YMR
                        url = root_path + row[x] #there was a bug here @V2.0 - YMR
                else:
                    if row[x].startswith('./'):
                        root_path = get_root_path(row[1], 1)
                        url = root_path + row[x].lstrip('.')
                    else:
                        url = row[x]
                
                try:
                    #apps2.shareholder is the third party noise link that gives stock data
                    #.php is a redirect link to share (FB, LinkedIn, Twitter)
                    if 'apps2.shareholder' not in url and ".php" not in url:
                        url2 = urllib.parse.quote_plus(url,'/:!#$%^&*()_-+=[]{}?', 'utf-8')
                        url2_path = urllib.parse.urlparse(url).path
                        #sometimes it may be .jpg, .png
                        ext = os.path.splitext(url2_path)[1]
                        name =  row[0] + "_PR" + str(x-1) + "_" + date
                        response = get_html(url2)
                        #if there is are no errors in opening up the socket connection then download
                        if response:
                            print("this is the modified_url of ", url2)
                            if b'PDF' not in response[:6]: 
                                if not ext:
                                    ext = '.html'
                                if 'html' in ext:
                                    ext = '.html'
                                print('this is my extension {0}'.format(ext))
                                with open(html_directory + "/" + name + ext, 'wb') as out_file:
                                    print(html_directory + "/" + name + ext)
                                    out_file.write(response)
#                                html_count += 1 #there was a bug here @V2.0 - YMR
                                flag = True

                            else:
                                print("\n------we will attempt to download a PDF instead\n")
                                pdf_name =  row[0] + "_PR" + str(x-1) + "_" + date #there was a bug here @V2.0 - YMR
                                pdf_response = get_pdf(url2)

                                if pdf_response:
                                    with open(pdf_directory + "/" + pdf_name + '.pdf', 'wb') as out_file:
                                        out_file.write(pdf_response)
                                    flag = True
                except Exception as e:
                    print('error in get_PR function:', e)
                    pass



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
    print('succesful update of SQL DB: ', sql_ip)        

my_file = Path(path + "top_39_pharma_companies_PR_cache_ref.csv")
if my_file.is_file():   #checks if a reference file exists
    #save the data table with drug name, company name and company website to a newly created csv file
    with open(path + 'top_39_pharma_companies_PR_cache_new.csv', 'w', encoding='utf-8-sig') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
        thedatawriter.writerow(Header)
        for row in data:
            thedatawriter.writerow(row)
    #re-open reference data file and read it as a csv file
    f = open(path + "top_39_pharma_companies_PR_cache_new.csv", encoding='utf-8-sig')
    csv_f = csv.reader(f)
    #initialize a blank list
    data_2 = []           # should we be rewriting the original data list?
    #append each row of the csv file to the list data
    for row in csv_f:
        data_2.append(row) # this data should have the same data as before
    #save the headers to Header and remove them for the list    
    Header = data_2[0] #there was a bug here @V2.0 - YMR
    data_2.pop(0)       
    #open reference data file and read it as a csv file
    f = open(path + "top_39_pharma_companies_PR_cache_ref.csv", encoding='utf-8-sig')
    csv_f = csv.reader(f)
    #initialize a blank list
    data_ref = []
    #append each row of the csv file to the list data
    for row in csv_f:
        data_ref.append(row)
    #save the headers to Header and remove them for the list    
    Header_ref = data_ref[0]
    data_ref.pop(0)
    with open(path + 'top_39_pharma_companies_PR_cache_ref_old.csv', 'w', encoding='utf-8-sig') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
        thedatawriter.writerow(Header_ref)
        for row in data_ref:
            thedatawriter.writerow(row)
            
    #save new file as ref file for next execution
    with open(path + 'top_39_pharma_companies_PR_cache_ref.csv', 'w', encoding='utf-8-sig') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
        thedatawriter.writerow(Header)
        for row in data:
            thedatawriter.writerow(row)
            
    new_PR = []
    l=0

    for k, row in enumerate(data_2):    #data has the new PR data
        #if row != data_ref[data.index(row)] and len(data[data.index(row)][3])>1:
        end = data_ref[k].count('')
        for m in range(0,end):  #removes empty list elements to compare ref vs new
            data_ref[k].remove('')
        if row != data_ref[k]:

            A[k+1][0]=row[0]    #company name
            A[k+1][1]=row[2]    #company's PR website
            #print('company:', row[0])
            for x in range(3, col): #loops through all possible PR links in data 
                try:
                    #removes '[' and ']' from the row string to convert it back to a list
                    striped_data = row[x][1:(len(row[x])-1)]
                    striped_data_ref = data_ref[k][x][1:(len(data_ref[k][x])-1)]
                    #converts the string back to a list
                    data_list = striped_data.split(',')
                    data_ref_list = striped_data_ref.split(',')

                    for l,link in enumerate(data_list):
                        data_list[l] = link.strip()
                    for l,link in enumerate(data_list):
                        data_list[l] = link.strip("'")

                    for l,link in enumerate(data_ref_list):
                        data_ref_list[l] = link.strip()
                    for l,link in enumerate(data_ref_list):
                        data_ref_list[l] = link.strip("'")

                    set_data_ref = set(data_ref_list)   #creates a list with unique elements
                    #creates a list with elements unique to new PR data
                    differences = [x for x in data_list if x not in set_data_ref]
                    differences = set(differences)
                    l=0
                    #print(differences)
                    for diff in differences:
                        diff = diff.strip()
                        diff = diff.strip('\'')
                        A[k+1][2+l]=diff    #saves only the new links that may be PR links
                        l+=1
                except Exception:
                    1+1

    print(A)
    if l==0:
        print('No new PR found')

    #save the list of new PRto a csv file        
    with open(path + 'new_PR.csv', 'w', encoding='utf-8') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
        #thedatawriter.writerow(new_PR)
        for row in A:
            if len(row[2])>0:
                thedatawriter.writerow(row)
                
    
    '''
    This part of the code handles SQL table update for PR source url tracking
    '''
    #satck A into a data frame
    df_ls = []
    for row_idx, row in enumerate(A):
        if len(row[2])>0 and row_idx>0:
            date_PR = datetime.date.today().strftime("%d-%m-%Y") #French format...
            for link_idx in range(98):
                if len(row[2 + link_idx])>0:
                    solr_id = row[0] + '_PR' + str(link_idx+1) + '_' + date_PR
                    
                    web_url = row[2 + link_idx]
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
        
        update_SQL_through_flask(df, "52.23.161.54")   
    except Exception as e:
        print('error updating the new AWS server SQL DB: ', e)       
    

    #write PR summary to a text file
    """
    with open(path + 'new_PR_summary.txt', 'w', encoding='utf-8') as f:
        #k=0
        r=0 #failed PR access iteration variable
        #for k, row in enumerate(A):
        #    get_PR(A, row, f, k, col)
    """  


    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:

        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(get_PR, A, row, f, k, col, 'PR'): row for k, row in enumerate(A)} #get_PR(A, row, f, k, col)
        for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
            #url = future_to_url[future]
            u = i

else:
    #save the data table with drug name, company name and compnay website to a newly created csv file    
    with open(path + 'top_39_pharma_companies_PR_cache_ref.csv', 'w', encoding='utf-8-sig') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
        thedatawriter.writerow(Header)
        for row in data:
            try:
                thedatawriter.writerow(row)
            except Exception:
                print('not able to write this row to csv')
                thedatawriter.writerow('missing row')
                


#write failed list to csv file
with open(path + 'failed_list.csv', 'w', encoding='utf-8-sig') as mycsvfile:
    thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
    for row in A_FL:
        thedatawriter.writerow(row)
        
#write timing for each company's PR website access to csv file
with open(path + 'PR_access_timing.csv', 'w', encoding='utf-8-sig') as mycsvfile:
    thedatawriter = csv.writer(mycsvfile, lineterminator = '\n')
    for row in A_timing:
        thedatawriter.writerow(row)

with open(path + 'new_PR_summary2.txt', 'w', encoding='utf-8') as f:
    for row in A_summary:
        if len(row[0])>0:
            f.write('\n')
            f.write('\n')
        for item in row:
            try:
                if item.startswith("http:"):
                    f.write('\n')
                f.write(item)
                f.write('\n')
            except Exception:
                1+1
                
                
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

print("---------- THESE ARE THE FAILED LINKS -----------\n")

for i, url in enumerate(fail):
    print(str(i), ": ", url, "\n")

print("---------------------\n")


print("--- %s seconds ---" % round(time.clock() - start_time, 2))

print("\n\n CODE EXECUTION COMPLETED")


    
    
    
