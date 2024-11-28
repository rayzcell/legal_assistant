import argparse
import logging
import json
import http.client
import urllib.parse
import os
import codecs

class IKApi:
    def __init__(self, args, storage):
        self.logger = logging.getLogger('ikapi')
        self.headers = {
            'Authorization': f'Token {args.token}',
            'Accept': 'application/json'
        }
        self.basehost = 'api.indiankanoon.org'
        self.storage = storage
        self.maxpages = args.maxpages if args.maxpages <= 100 else 100

    def call_api(self, url):
        connection = http.client.HTTPSConnection(self.basehost)
        connection.request('POST', url, headers=self.headers)
        response = connection.getresponse()
        results = response.read()
        return results

    def fetch_doc(self, docid):
        url = f'/doc/{docid}/'
        json_data = self.call_api(url)
        data = json.loads(json_data)
        
        # Extract only title and main document text if available
        if 'title' in data and 'doc' in data:
            title = data['title']
            main_text = data['doc']
            return {'title': title, 'text': main_text}
        else:
            self.logger.warning("Title or text missing in document %d", docid)
            return None

    def save_doc_text(self, docid):
        doc_data = self.fetch_doc(docid)
        if doc_data:
            # Save document as JSON file in the specified data directory
            filename = os.path.join(self.storage.datadir, f"{docid}_summary_input.json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, ensure_ascii=False, indent=4)
            self.logger.info("Saved title and text for document %d", docid)
        else:
            self.logger.warning("Failed to save document %d", docid)

    def download_search_results(self, query):
        pagenum = 0
        while pagenum < self.maxpages:
            encoded_query = urllib.parse.quote_plus(query)
            url = f'/search/?formInput={encoded_query}&pagenum={pagenum}&maxpages=1'
            results = self.call_api(url)
            print(results)
            obj = json.loads(results)

            if 'docs' not in obj or not obj['docs']:
                break

            for doc in obj['docs']:
                docid = doc['tid']
                self.save_doc_text(docid)

            pagenum += 1

class FileStorage:
    def __init__(self, datadir):
        self.datadir = datadir
        if not os.path.exists(datadir):
            os.makedirs(datadir)

    def save_json(self, results, filepath):
        """Save JSON content to a file."""
        with codecs.open(filepath, mode='w', encoding='utf-8') as f:
            f.write(results)

def get_arg_parser():
    parser = argparse.ArgumentParser(description="Download title and text from api.indiankanoon.org")
    parser.add_argument('-t', '--token', required=True, help='API token for Indian Kanoon')
    parser.add_argument('-d', '--datadir', required=True, help='Directory to save files')
    parser.add_argument('-q', '--query', required=True, help='Search query for cases')
    parser.add_argument('-p', '--maxpages', type=int, default=1, help='Maximum number of search pages to download')
    return parser

def setup_logging(loglevel='info', logfile=None):
    logformat = '%(asctime)s: %(message)s'
    dateformat = '%Y-%m-%d %H:%M:%S'
    loglevel_dict = {
        'critical': logging.CRITICAL,
        'error': logging.ERROR,
        'warning': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG
    }
    loglevel = loglevel_dict.get(loglevel.lower(), logging.INFO)
    
    if logfile:
        logging.basicConfig(filename=logfile, level=loglevel, format=logformat, datefmt=dateformat)
    else:
        logging.basicConfig(level=loglevel, format=logformat, datefmt=dateformat)

if __name__ == '__main__':
    parser = get_arg_parser()
    args = parser.parse_args()

    setup_logging()
    filestorage = FileStorage(args.datadir)
    ikapi = IKApi(args, filestorage)

    ikapi.download_search_results(args.query)
