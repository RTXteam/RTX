import requests
from time import sleep
from bs4 import BeautifulSoup
import random
import sys

#   retrieve data from URL
def retrieve(url: str):
    #   retrieves content at the specified url
    print("*", url)
    sleep(1)  # *never* web scrape faster than 1 request per second
    UAS = ("Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1",
           "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0",
           "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0",
           "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
           "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36",
           "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
           "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36"
           )
    ua = UAS[random.randrange(len(UAS))]
    headers = {'user-agent': ua, 'Cache-Control': 'no-cache'}
    try:
        r = requests.get(url, headers=headers, verify=False)  # get the HTML; ignore SSL errors (present on this particular site)
    except BaseException as e:
        print(url, file=sys.stderr)
        print('%s received for URL: %s' % (e, url), file=sys.stderr)
        return None
    soup = BeautifulSoup(r.text, "lxml")  # parse the HTML
    return soup


