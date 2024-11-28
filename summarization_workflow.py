import json
import logging
from transformers import pipeline
import argparse
import logging
import os
import re
import codecs
import json
import http.client
import urllib.request, urllib.parse, urllib.error
import base64
import glob
import csv
import datetime
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ikapi')


class FileStorage:
    def __init__(self, datadir):
        self.datadir = datadir

    def save_json(self, results, filepath):
        json_doc  = results.decode('utf8')
        json_file = codecs.open(filepath, mode = 'w', encoding = 'utf-8')
        json_file.write(json_doc)
        json_file.close()

    def exists(self, filepath):
        if os.path.exists(filepath):
            return True
        else:
            return False

    def exists_original(self, origpath):
        return glob.glob('%s.*' % origpath)

    def get_docpath(self, docsource, publishdate):
        datadir = os.path.join(self.datadir, docsource)
        mk_dir(datadir)

        d = get_dateobj(publishdate)
        datadir = os.path.join(datadir, '%d' % d.year)
        mk_dir(datadir)

        docpath = os.path.join(datadir, '%s' % d)
        mk_dir(docpath)

        return docpath

    def get_file_extension(self, mtype):
        t = 'unkwn'
        if not mtype:
            print (mtype)
        elif re.match('text/html', mtype):
            t = 'html'
        elif re.match('application/postscript', mtype):
            t = 'ps'
        elif re.match('application/pdf', mtype):
            t = 'pdf'
        elif re.match('text/plain', mtype):
            t = 'txt'
        elif re.match('image/png', mtype):
            t = 'png'
        return t 

    def save_original(self, orig, origpath):
        obj = json.loads(orig)
        if 'errmsg' in obj:
            return

        doc = base64.b64decode(obj['doc'])

        extension = self.get_file_extension(obj['Content-Type'])

        filepath   = origpath + '.%s' % extension
        filehandle = open(filepath, 'wb')
        filehandle.write(doc)
        filehandle.close()

    def get_docpath_by_docid(self, docid):
        docpath = os.path.join(self.datadir, '%d' % docid)
        mk_dir(docpath)
        return docpath

    def get_json_orig_path(self, docpath, docid):
        jsonpath = os.path.join(docpath, '%d.json' % docid)
        origpath = os.path.join(docpath, '%d_original' % docid)
        return jsonpath, origpath

    def get_json_path(self, q):
        jsonpath = os.path.join(self.datadir, '%s.json' % q)
        return jsonpath

    def get_search_path(self, q):
        datadir = os.path.join(self.datadir, q)
        mk_dir(datadir)
        return datadir

    def get_tocwriter(self, datadir):
        fieldnames = ['position', 'docid', 'date', 'court', 'title']
        tocfile   = os.path.join(datadir, 'toc.csv')
        tochandle = open(tocfile, 'w', encoding = 'utf8')
        tocwriter = csv.DictWriter(tochandle, fieldnames=fieldnames)
        tocwriter.writeheader()
        return tocwriter

    def get_docpath_by_position(self, datadir, current):
        docpath = os.path.join(datadir, '%d' % current)
        mk_dir(docpath)
        return docpath
def get_dateobj(datestr):
    ds = re.findall('\d+', datestr)
    return datetime.date(int(ds[0]), int(ds[1]), int(ds[2]))

def mk_dir(datadir):
    if not os.path.exists(datadir):
        os.mkdir(datadir)


class Summarizer:
    """Handles text summarization using a Hugging Face model."""
    def __init__(self):
        self.summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

    def summarize(self, text, max_length=150, min_length=50):
        """Summarizes the given text."""
        try:
            return self.summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)[0]["summary_text"]
        except Exception as e:
            logger.error(f"Failed to summarize text: {e}")
            return "Error in summarization."

def get_related_case_summaries(api, query, summarizer, max_results=10):
    """
    Searches for related cases based on a query, fetches their details, and summarizes them.

    Args:
        api (IKApi): The Indian Kanoon API client.
        query (str): The search query.
        summarizer (Summarizer): Summarizer instance for summarizing case details.
        max_results (int): Maximum number of cases to summarize.

    Returns:
        list[dict]: List of summarized case details.
    """
    summaries = []
    try:
        logger.info(f"Searching for cases related to query: {query}")
        search_results = api.search(query, pagenum=0, maxpages=max_results)
        search_data = json.loads(search_results)

        if "docs" not in search_data or not search_data["docs"]:
            logger.warning("No related cases found.")
            return summaries

        for case in search_data["docs"]:
            docid = case["tid"]
            title = case["title"]
            logger.info(f"Fetchingc details for case ID: {docid} - {title}")

            # Fetch case details
            case_data = api.fetch_doc(docid)
            if not case_data:
                logger.warning(f"Failed to fetch details for case ID: {docid}")
                continue

            # Parse and summarize the main text
            case_json = json.loads(case_data)
            main_text = case_json.get("text", "No main text available.")
            summary = summarizer.summarize(main_text)
            summaries.append({"title": title, "summary": summary})

            # Stop if max_results limit is reached
            if len(summaries) >= max_results:
                break

    except Exception as e:
        logger.error(f"Error during case processing: {e}")

    return summaries
class IKApi:
    def __init__(self, args, storage):
        self.logger     = logging.getLogger('ikapi')

        self.headers    = {'Authorization': 'Token %s' % args.token, \
                           'Accept': 'application/json'}

        self.basehost   = 'api.indiankanoon.org'
        self.storage    = storage
        #self.maxcites   = args.maxcites
        #self.maxcitedby = args.maxcitedby
        #self.orig       = args.orig
        #self.maxpages   = args.maxpages
        #self.pathbysrc  = args.pathbysrc

        #if self.maxpages > 100:
            #self.maxpages = 100

    def call_api(self, url):
        connection = http.client.HTTPSConnection(self.basehost)
        connection.request('POST', url, headers = self.headers)
        response = connection.getresponse()
        results = response.read()
        return results 
    
    def fetch_doc(self, docid):
        url = '/doc/%d/' % docid

        args = []
        #if self.maxcites > 0:
            #args.append('maxcites=%d' % self.maxcites)

        #if self.maxcitedby > 0:
            #args.append('maxcitedby=%d' % self.maxcitedby)

        if args:
            url = url + '?' + '&'.join(args)

        return self.call_api(url)



    def fetch_docmeta(self, docid):
        url = '/docmeta/%d/' % docid

        args = []
        if self.maxcites != 0:
            args.append('maxcites=%d' % self.maxcites)

        if self.maxcitedby != 0:
            args.append('maxcitedby=%d' % self.maxcitedby)

        if args:
            url = url + '?' + '&'.join(args)

        return self.call_api(url)

    def fetch_orig_doc(self, docid):
        url = '/origdoc/%d/' % docid
        return self.call_api(url)

    def fetch_doc_fragment(self, docid, q):
        q   = urllib.parse.quote_plus(q.encode('utf8'))
        url = '/docfragment/%d/?formInput=%s' % (docid,  q)
        return self.call_api(url)

    def search(self, q, pagenum, maxpages):
        q = urllib.parse.quote_plus(q.encode('utf8'))
        url = '/search/?formInput=%s&pagenum=%d&maxpages=%d' % (q, pagenum, maxpages)
        return self.call_api(url)


    def save_doc_fragment(self, docid, q):
        success = False

        jsonstr = self.fetch_doc_fragment(docid, q)
        if not jsonstr:
            return False

        jsonpath = self.storage.get_json_path('%d q: %s' % (docid, q))
        success = self.storage.save_json(jsonstr, jsonpath)
        return success    

    def download_doc(self, docid, docpath):    
        success = False
        orig_needed = self.orig
        jsonpath, origpath = self.storage.get_json_orig_path(docpath, docid)

        if not self.storage.exists(jsonpath):
            jsonstr = self.fetch_doc(docid)
            d = json.loads(jsonstr)
            if 'errmsg' in d:
                return success
        
            self.logger.info('Saved %s', d['title'])
            self.storage.save_json(jsonstr, jsonpath)
            success = True

            if orig_needed:
                if not d['courtcopy']:
                    orig_needed = False

        if orig_needed and not self.storage.exists_original(origpath):
            orig = self.fetch_orig_doc(docid)
            if orig:
                self.logger.info('Saved Original %s', d['title'])
                self.storage.save_original(orig, origpath)
        return success        

    def download_doctype(self, doctype, fromdate, todate):
        q = 'doctypes: %s' % doctype
        if fromdate:
            q += ' fromdate: %s' % fromdate
        if todate:
            q += ' todate: %s' % todate

        pagenum = 0
        docids = []
        while 1:
            results = self.search(q, pagenum, self.maxpages)
            obj = json.loads(results)
 
            if 'docs' not in obj or len(obj['docs']) <= 0:
                break
            docs = obj['docs']
            self.logger.warning('Num results: %d, pagenum: %d', len(docs), pagenum)
            for doc in docs:
                docpath = self.storage.get_docpath(doc['docsource'], doc['publishdate'])
                if self.download_doc(doc['tid'], docpath):
                    docids.append(doc['tid'])

            pagenum += self.maxpages 

        return docids

    def save_search_results(self, q):
        datadir = self.storage.get_search_path(q)

        tocwriter = self.storage.get_tocwriter(datadir)

        pagenum = 0
        current = 1
        docids  = []
        while 1:
            results = self.search(args.q, pagenum, self.maxpages)
            obj = json.loads(results)

            docs = obj['docs']
            if len(docs) <= 0:
                break
            self.logger.warning('Num results: %d, pagenum: %d', len(docs), pagenum)

            for doc in docs:
                docid = doc['tid']
                title = doc['title']
                toc = {'docid': docid, 'title': title, 'position': current, \
                       'date': doc['publishdate'], 'court': doc['docsource']}
                tocwriter.writerow(toc)

                if self.pathbysrc:
                    docpath = self.storage.get_docpath(doc['docsource'], doc['publishdate'])
                else:    
                    docpath = self.storage.get_docpath_by_position(datadir, current)
                if self.download_doc(docid, docpath):
                    docids.append(docid)
                current += 1

            pagenum += self.maxpages 
        return docids


if __name__ == "__main__":
    from argparse import ArgumentParser

    # Argument parser for the Indian Kanoon API client
    parser = ArgumentParser()
    parser.add_argument("--token", required=True, help="Indian Kanoon API token.")
    #parser.add_argument("--query", required=True, help="Search query for related cases.")
    parser.add_argument("--datadir", required=True, help="Directory to store case data.")
    args = parser.parse_args()

    # Initialize the Indian Kanoon API client and summarizer
    storage = FileStorage(args.datadir)
    api = IKApi(args, storage)
    summarizer = Summarizer()


    #ikapi = IKApi(maxpages=5)
    #ikapi = IKApi()

    # Fetch and process the case
    docid = 119259277

    case_details = api.fetch_doc( docid)
    #print(case_details)
    #title = case_details['title']
 
    # Fetch and summarize related cases
    summaries = get_related_case_summaries(api, case_details, summarizer)

    # Output the summaries
    for case_summary in summaries:
        print(f"Title: {case_summary['title']}\nSummary: {case_summary['summary']}\n")
