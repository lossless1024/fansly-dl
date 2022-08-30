import os
import sys
import json
from json import JSONDecodeError

import requests
import logging
import datetime

with open('config.json', 'rb') as f:
    config = json.load(f)

headers = {
    'User-Agent': config['user-agent'],
    'authorization': config['token']
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

API_URL = 'https://apiv3.fansly.com/api/v1/'


class Fetch:
    def __init__(self, endpoint, relevant_field=None, limit=25, offset_field='before', id_field='id', paged=True):
        self.endpoint = endpoint
        self.endpoint_data_delimiter = '&' if '?' in self.endpoint else '?'
        self.relevant_field = relevant_field or 'response'
        self.expect_subtree = relevant_field is not None
        self.limit = limit
        self.offset_field = offset_field
        self.id_field = id_field
        self.paged = paged
        self.current_post_index = 0
        self.last_post = 0
        self.hit_end = False
        self.data = {}
        self.fetch_more()

    @property
    def downloaded_posts_count(self):
        if self.relevant_field not in self.data:
            return 0

        return len(self.data[self.relevant_field])

    def __iter__(self):
        self.current_post_index = 0
        return self

    def __next__(self):
        if self.downloaded_posts_count == 0:
            raise StopIteration

        if self.current_post_index == self.downloaded_posts_count:
            if self.paged:
                if self.fetch_more():
                    return self.__next__()
        elif self.downloaded_posts_count > 0:
            self.current_post_index += 1
            return self.data[self.relevant_field][self.current_post_index - 1]
        raise StopIteration

    def fetch_more(self):
        logging.debug(self.endpoint)
        count_before_fetch = self.downloaded_posts_count
        url = self.endpoint + self.endpoint_data_delimiter + self.offset_field + ('=%d&after=0' % self.last_post)
        try:
            response = requests.get(API_URL + url, headers=headers)
            response = response.json()
        except JSONDecodeError:
            return False

        if not response['success']:
            logging.critical('Failed to fetch ' + url)
            sys.exit(1)

        if self.expect_subtree:
            response = response['response']

        if self.relevant_field not in response:
            return False

        if not response[self.relevant_field]:
            return False

        if type(response) is dict:
            for obj in response:
                if response[obj]:
                    if obj not in self.data:
                        self.data[obj] = response[obj]
                    elif not isinstance(response[obj], type(self.data[obj])):
                        logging.critical('Mismatching types found while fetching ' + url)
                    elif type(self.data[obj]) is list:
                        self.data[obj].extend(response[obj])
                    elif obj == 'stats' and type(self.data[obj]) is dict:
                        pass
                    else:
                        logging.critical('Unsupported object type found while fetching ' + url)
        else:
            logging.critical('Unsupported response data type found while fetching ' + url)

        for post in response[self.relevant_field]:
            self.last_post = int(post[self.id_field])

        if self.downloaded_posts_count == count_before_fetch:
            return False

        return self.data

    def fetch_all(self):
        while self.fetch_more() and self.paged:
            pass

        return self.data


def download_media(data, folder):
    if data['locations']:
        url = data['locations'][0]['location']
        cdn_filename = data['filename'] if 'filename' in data else data['location'].split('/')[-1]
        filename = datetime.datetime.utcfromtimestamp(data['createdAt']).strftime('%Y%m%d_%H%M%S_') + cdn_filename
        if filename.endswith('.mp4'):
            os.makedirs(folder + 'vid', exist_ok=True)
            filename = 'vid/' + filename
        elif filename.endswith('.jpg') or filename.endswith('.png') or filename.endswith('.gif'):
            os.makedirs(folder + 'pic', exist_ok=True)
            filename = 'pic/' + filename
        full_dl_path = folder + filename
        if not os.path.exists(full_dl_path):
            with open(full_dl_path, 'wb') as f:
                logging.info('Saving ' + cdn_filename)
                f.write(requests.get(url, headers=headers).content)
        else:
            return False
    else:
        logging.warning('Media without URL')
    return True


def main():
    logging.info('Fetching user data')
    subscriptions = Fetch('subscriptions', 'subscriptions', paged=False).fetch_all()
    accountIds = list(map(lambda a: a['accountId'], subscriptions['subscriptions']))
    accountUsernames = {}

    accounts = Fetch('account?ids=' + ','.join(accountIds), paged=False)
    for account in accounts:
        logging.info('Downloading account ' + account['username'])
        accountUsernames[account['id']] = account['username']
        folder = '%s/%s/' % (config['download_folder'], account['username'])

        posts = Fetch('timeline/' + account['id'], 'posts')
        hit_end = False
        for post in posts:
            for media in post['attachments']:
                mediaIds = sum([x['accountMediaIds'] for x in posts.data['accountMediaBundles'] if x['id'] == media['contentId']], [])
                mediaIds.extend([x['id'] for x in posts.data['accountMedia'] if x['id'] == media['contentId']])

                for mediaId in mediaIds:
                    data = next(x for x in posts.data['accountMedia'] if x['id'] == mediaId)['media']
                    if not download_media(data, folder):
                        hit_end = config['quick_fetch']
            if hit_end:
                break

    groups = Fetch('messaging/groups?sortOrder=1&flags=0&subscriptionTierId=&search=&limit=25', 'data', offset_field='offset', id_field='groupId')
    for group in groups:
        logging.info('Downloading messages with ' + accountUsernames[group['partnerAccountId']])
        folder = '%s/%s/msg_' % (config['download_folder'], accountUsernames[group['partnerAccountId']])

        messages = Fetch('message?groupId=' + group['groupId'], 'messages')
        hit_end = False
        for message in messages:
            if message['senderId'] == group['account_id']:
                continue  # Do not download my pics

            for media in message['attachments']:
                mediaIds = []
                if 'accountMediaBundles' in messages.data:
                    mediaIds.extend(sum([x['accountMediaIds'] for x in messages.data['accountMediaBundles'] if x['id'] == media['contentId']], []))
                if 'accountMedia' in messages.data:
                    mediaIds.extend([x['id'] for x in messages.data['accountMedia'] if x['id'] == media['contentId']])

                for mediaId in mediaIds:
                    data = next(x for x in messages.data['accountMedia'] if x['id'] == mediaId)['media']
                    if not download_media(data, folder):
                        hit_end = config['quick_fetch']
            if hit_end:
                break

main()