import os
import sys
import json
import requests
import logging
import datetime


with open('config.json', 'rb') as f:
    config = json.load(f)

headers = {
    'authorization': config['token']
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

API_URL = 'https://apiv2.fansly.com/api/v1/'

subscriptions = requests.get(API_URL + 'subscriptions', headers=headers).json()
if not subscriptions['success']:
    logging.critical('Failed to fetch subscriptions')
    sys.exit(1)
accountIds = list(map(lambda a: a['accountId'], subscriptions['response']['subscriptions']))

accounts = requests.get(API_URL + 'account?ids=' + ','.join(accountIds)).json()
if not accounts['success']:
    logging.critical('Failed to fetch accounts')
    sys.exit(1)


for account in accounts['response']:
    logging.info('Downloading account ' + account['username'])
    folder = '%s/%s/' % (config['download_folder'], account['username'])
    os.makedirs(folder + 'vid', exist_ok=True)
    os.makedirs(folder + 'pic', exist_ok=True)

    last_post = 0
    hit_end = False
    while not hit_end:
        resp = requests.get(API_URL + 'timeline/%s?before=%d&after=0' % (account['id'], last_post),
                            headers=headers).json()
        if not resp['success']:
            logging.critical('Failed to fetch timeline')
            break

        if not resp['response']['posts']:
            break

        for media in resp['response']['accountMedia']:
            data = media['media']
            if data['locations']:
                url = data['locations'][0]['location']
                filename = datetime.datetime.utcfromtimestamp(data['createdAt']).strftime('%Y%m%d_%H%M%S_') + data['filename']
                if filename.endswith('.mp4'):
                    filename = 'vid/' + filename
                elif filename.endswith('.jpg') or filename.endswith('.png') or filename.endswith('.gif'):
                    filename = 'pic/' + filename
                full_dl_path = folder + filename
                if not os.path.exists(full_dl_path):
                    with open(full_dl_path, 'wb') as f:
                        logging.info('Fetching ' + data['filename'])
                        f.write(requests.get(url).content)
                else:
                    hit_end = config['quick_fetch']

        for post in resp['response']['posts']:
            last_post = int(post['id'])
