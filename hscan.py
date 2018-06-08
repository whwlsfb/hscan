#!/usr/bin/python
# encoding=utf-8

import requests
import time
import sys
import json
from collections import defaultdict
import re
import datetime
import schedule

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

config = []


class switch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration

    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args:
            self.fall = True
            return True
        else:
            return False


def humantime2minutes(s):
    d = {
        'w':      7*24*60,
        'week':   7*24*60,
        'weeks':  7*24*60,
        'd':      24*60,
        'day':    24*60,
        'days':   24*60,
        'h':      60,
        'hr':     60,
        'hour':   60,
        'hours':  60,
    }
    mult_items = defaultdict(lambda: 1).copy()
    mult_items.update(d)

    parts = re.search(r'^(\d+)([^\d]*)', s.lower().replace(' ', ''))
    if parts:
        return int(parts.group(1)) * mult_items[parts.group(2)] + humantime2minutes(re.sub(r'^(\d+)([^\d]*)', '', s.lower()))
    else:
        return 0


def get_check(item):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
    }
    resp = requests.get(item['url'], headers=headers,
                        verify=False, allow_redirects=True)
    return resp


def head_check(item):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
    }
    resp = requests.head(item['url'], headers=headers,
                         verify=False, allow_redirects=True)
    return resp


def post_check(item):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }
    resp = requests.post(
        item['url'], data=item['data'], headers=headers, verify=False, allow_redirects=True)
    return resp


def result_check(resp, item):
    for match in item['matchs']:
        parms = match['parms']
        result = False
        for case in switch(match['matchmethod']):
            if case("StatusCode"):
                if resp.status_code == parms['status_code']:
                    result = True
                break
            if case("Contain"):
                if parms['text'] in resp.text:
                    result = True
                break
            if case("NotContain"):
                if parms['text'] not in resp.text:
                    result = True
                break
        if (item['allmatch'] == 'true'):
            if (not result):
                return False, match
        elif (result):
            return True, None
    return True, None


def check(item):
    global config
    checkmethod = item['checkmethod']
    resp = None
    result = False
    error = None
    match = None
    for i in range(config['connectionSetting']['retrycount']):
        try:
            for case in switch(checkmethod):
                if case("GET"):
                    resp = get_check(item)
                    break
                if case("HEAD"):
                    resp = head_check(item)
                    break
                if case("POST"):
                    resp = post_check(item)
                    break
            result, match = result_check(resp, item)
            break
        except Exception as ex:
            error = ex
    print('[I] %s check result, Alive: %s' % (item['name'], result))
    if (not result):
        if (not item['dead']):
            alert(item, resp, match, error)
    else:
        if (item['dead']):
            recovery(item)
    item['dead'] = not result

def recovery(item):
    global config
    name = item['name']
    print('[+] %s is recovery! Collecting information...' % name)
    alert_title = '网站 %s 已恢复正常！' % name
    alert_content = '''地址：%s\n\n时间：%s''' % (item['url'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    sendto_alertgroup(alert_title,alert_content,item['alertgroup'])

def alert(item, resp, match, ex):
    global config
    name = item['name']
    print('[-] %s is dead! Collecting information...' % name)
    alert_title = '网站 %s 出现故障！' % name
    alert_content = '''地址：%s\n\n时间：%s''' % (item['url'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if not resp == None:
        alert_content += '\n\n状态码：%d' % resp.status_code
    if not match == None:
        alert_content += '\n\n故障匹配信息："%s","%s"' % (
            match['matchmethod'], match['parms'])
    if not ex == None:
        alert_content += '\n\nPython异常：%s' % ex
    alert_content += '\n\n以上为异常全部信息，请及时处理！'
    print('---------------\n%s\n%s\n---------------' % (alert_title, alert_content))
    sendto_alertgroup(alert_title,alert_content,item['alertgroup'])

def sendto_alertgroup(title, content, alertgroupname):
    global config
    alertgroup = config['alertgroup'][alertgroupname]
    for alert in alertgroup:
        alertmethod = alert['alertmethod']
        for case in switch(alertmethod):
            print('[=] Sendto %s, parms:%s' % (alertmethod, alert['parms']))
            try:
                if case("ServerChan"):
                    sendto_serverchan(alert['parms'], title, content)
                    break
                if case("PushBear"):
                    sendto_pushbear(alert['parms'], title, content)
                    break
            except Exception as ex:
                print(ex)

def load_tasks():
    global config
    print('[+] tasks loading...')
    for item in config['items']:
        print('''---------------
Name: %s
Url: %s
Rate: %s
AlertGroup: %s
---------------''' % (item['name'], item['url'], item['rate'], item['alertgroup']))
        item['dead'] = False
        min = humantime2minutes(item['rate'])
        #schedule.every(5).seconds.do(check, item)
        schedule.every(min).minutes.do(check, item)
    print('[+] task loading finish.')

def sendto_pushbear(parms, subject, content):
    data = {
        'sendkey': parms['sendkey'],
        'text': subject,
        'desp': content
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }
    resp = requests.post('https://pushbear.ftqq.com/sub', data=data, headers=headers, verify=False, allow_redirects=True)
    print(resp)

def sendto_serverchan(parms, subject, content):
    data = {
        'text': subject,
        'desp': content
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }
    resp = requests.post('https://sc.ftqq.com/%s.send' %
                         parms['sckey'], data=data, headers=headers, verify=False, allow_redirects=True)
    print(resp)


if __name__ == "__main__":
    config_file = "config.json"
    if len(sys.argv) > 2:
        config_file = sys.argv[2]
    print('[+] using config file %s' % config_file)
    config = json.loads(open(config_file, encoding="utf-8").read())
    load_tasks()
    print('[=] start doing...')
    while True:
        schedule.run_pending()
        time.sleep(1)
