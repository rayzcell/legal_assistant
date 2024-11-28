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
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'  # Mimic a browser-like request
        }
        self.basehost = 'api.indiankanoon.org'
        self.storage = storage
        self.maxpages = min(args.maxpages, 100)  # Limit max pages to 100

    def call_api(self, url, method='POST'):
        """Calls the API with the specified URL and HTTP method, handling errors gracefully."""
        connection = http.client.HTTPSConnection(self.basehost)
        connection.request(method, url, headers=self.headers)
        response = connection.getresponse()

        # Check for HTTP status code
        if response.status != 200:
            self.logger.error(f"HTTP error {response.status}: {response.reason}")
            return None

        results = response.read()
        connection.close()
        return results

    def fetch_doc(self, docid):
        """Fetches a specific document by ID, returns title and main text if available."""
        url = f'/doc/{docid}/'
        json_data = self.call_api(url)
        
        if not json_data:
            self.logger.warning(f"No data received for document {docid}")
            return None

        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON for document {docid}")
            return None

        # Extract title and main text if available
        title = data.get('title', '')
        main_text = data.get('doc', '')
        
        if title and main_text:
            return {'title': title, 'text': main_text}
        else:
            self.logger.warning(f"Title or text missing in document {docid}")
            return None

    def save_doc_text(self, docid):
        """Fetches document by ID and saves it as a JSON file."""
        doc_data = self.fetch_doc(docid)
        if doc_data:
            filename = os.path.join(self.storage.datadir, f"{docid}_summary_input.json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, ensure_ascii=False, indent=4)
            self.logger.info(f"Saved title and text for document {docid}")
        else:
            self.logger.warning(f"Failed to save document {docid}")

    def download_search_results(self, query):
        """Downloads search results based on the query and saves documents in storage."""
        pagenum = 0
        while pagenum < self.maxpages:
            encoded_query = urllib.parse.quote_plus(query)
            url = f'/search/?formInput={encoded_query}&pagenum={pagenum}&maxpages=1'
            results = self.call_api(url)

            if not results:
                self.logger.warning("No results returned for the query.")
                break
            
            try:
                obj = json.loads(results)
            except json.JSONDecodeError:
                self.logger.error("Failed to decode JSON in search results.")
                break

            # If no docs found, exit the loop
            if 'docs' not in obj or not obj['docs']:
                self.logger.info("No more documents found.")
                break

            for doc in obj['docs']:
                docid = doc['tid']
                self.save_doc_text(docid)

            pagenum += 1

class FileStorage:
    def __init__(self, datadir):
        self.datadir = datadir
        os.makedirs(datadir, exist_ok=True)

    def save_json(self, results, filepath):
        """Saves JSON content to a file."""
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
