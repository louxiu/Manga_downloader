#!/usr/bin/env python

import cStringIO
import formatter
from htmllib import HTMLParser
import httplib
import os
import sys
import urllib
import urlparse
import re
import shutil
from time import sleep
import datetime
import tempfile

first_volume = 0
last_volume = 0
download_dir = ''

# TODO: Merge script_tag_HTMLParser and title_tag_HTMLParser
class script_tag_HTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, '')
        self.script_tag_count = 0
        self.images_items = ''
        
    def handle_starttag(self, tag, method, attrs):
        if tag != 'link':
            return

        # only fetch the first script tag
        self.script_tag_count += 1
        
    def handle_endtag(self, tag, method):
        return
    
    def handle_data(self, data):
        if self.script_tag_count == 1:
            self.script_tag_count = 2
            self.images_items = data

class title_tag_HTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, '')
        self.script_tag_count = 0
        self.title = ''
        
    def handle_starttag(self, tag, method, attrs):
        if tag != 'title':
            return

        self.script_tag_count += 1
        
    def handle_endtag(self, tag, method):
        return
    
    def handle_data(self, data):
        if self.script_tag_count == 1:
            self.script_tag_count = 2
            self.title = data

class Retriever(object):
    def __init__(self, url, save_file):
        self.url = url
        self.save_file = save_file

    def reset_url_save_file(self, url, save_file):
        self.url = url
        self.save_file = save_file
        
    def fetch_page(self):
        """
        """
        try:
            retval = urllib.urlretrieve(self.url, self.save_file)
        except (IOError, httplib.InvalidURL) as e:
            retval = (('*** ERROR: bad URL "%s": %s' % (self.url, e)),)
        return retval

    def parse_links(self):
        """fetch all links from page
        """
        f = open(self.save_file, 'r')
        data = f.read()
        f.close()
        parser = HTMLParser(formatter.AbstractFormatter(
            formatter.DumbWriter(cStringIO.StringIO())))
        parser.feed(data)
        parser.close()
        return parser.anchorlist

    def parse_title(self):
        """fetch the title of the book
        """
        f = open(self.save_file, 'r')
        data = f.read()
        f.close()
        parser = title_tag_HTMLParser()
        parser.feed(data)
        parser.close()
        return parser.title
        
    def parse_images_name(self):
        """fetch the names of images and path
        """
        f = open(self.save_file, 'r')
        data = f.read()
        f.close()
        parser = script_tag_HTMLParser()
        parser.feed(data)
        parser.close()
        return parser.images_items

class Crawler(object):
    def __init__(self, url):
        self.book_catalog_url = url
        _, self.catalog_page = tempfile.mkstemp()
        self.catalog_link_pattern = "http://dx.blgl8.com/manhua-v/"
        self.book_name = ''
        # TODO: use pair: (volume name, url)
        self.book_catalog = []
        self.images_url_base = "http://mh.jmymh.jmmh.net:2012/"
        
    def fetch_catalog_page(self):
        """The page contain books name and catalog
        """
        r = Retriever(self.book_catalog_url, self.catalog_page)
        catalog_page_file = r.fetch_page()

        if catalog_page_file[0] == '*':
            print "Fetch catalog page file fails"
            sys.exit()

        print "Fetch catalog page, YEAH"
        # TODO: Parse the name
        self.book_name = r.parse_title()
        self.book_name = re.sub('[\r\n\t]', '', self.book_name)
        
        print "The book name is %s " % self.book_name
    
        for link in r.parse_links():
            if link.startswith(self.catalog_link_pattern):
                self.book_catalog.append(link)

        os.remove(self.catalog_page)
        print 'There are %d volumes. YEAH' % len(self.book_catalog)

    def fetch_volume(self, volume_link, volume_name):
        # print the date
        now = datetime.datetime.now()
        print "Time %d:%d:%d" % (now.day, now.hour, now.minute)
        _, volume_page = tempfile.mkstemp()
        
        r = Retriever(volume_link, volume_page)
        volume_first_page_file = r.fetch_page()

        if volume_first_page_file[0] == '*':
            print "Fetch the first page of volume file fails"
            sys.exit()

        images_names = r.parse_images_name()
        os.remove(volume_page)
        
        info_parts = re.split('"', images_names)

        images_path = info_parts[3]
        images_names = re.split('\|', info_parts[1])

        # print images_path, images_names

        if os.path.exists("%s/%s/" % (download_dir, volume_name)):
            shutil.rmtree("%s/%s" % (download_dir, volume_name))

        os.makedirs("%s/%s" % (download_dir, volume_name))

        image_count = 0
        image_sum = len(images_names)

        print "Total %d " % image_sum
        for image_name in images_names:
            r = Retriever(self.images_url_base + images_path + image_name, ("/home/louxiu/Downloads/%s/" % volume_name) + image_name)
            print "%d" % image_count
            image_file = r.fetch_page()

            if image_file[0] == '*':
                print "Fetch image file fails"
                sys.exit()
            image_count += 1
            # TODO: what's wrong here?
            # print ("\r%d/%d" % image_count, image_sum).replace("\n", " ")
        sleep(10 * 60)            

    def fetch_volumes(self):
        volume_count = 1

        for volume_link in reversed(self.book_catalog):
            # skip to the first_volume
            if volume_count < int(first_volume):
                volume_count += 1;
                continue
            # break when out of last_volume
            if (int(last_volume) != 0) and (volume_count > int(last_volume)) :
                break
            print "start to download " + str(volume_count)
            self.fetch_volume(volume_link, "%s_%d" % (self.book_name, volume_count))
            volume_count += 1

    def go(self, media = False):
        self.fetch_catalog_page()
        self.fetch_volumes()

# manga_fetch.py url first_volume last_volume download_dir
# Example: manga_fetch.py url 1 2

def main():
    # TODO: Handle arguments carefully
    global first_volume, last_volume, download_dir
    
    category_url = sys.argv[1]
    first_volume = sys.argv[2]
    last_volume  = sys.argv[3]
    download_dir = sys.argv[4]
    download_dir.strip("/")
    
    robot = Crawler(category_url)
    robot.go()
    
if __name__ == '__main__':
    main()
