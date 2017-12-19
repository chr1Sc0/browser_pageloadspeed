#!/usr/bin/env python
# -*- coding: utf-8 -*-

#################################################
_FileName = "chrome_loadtest.py"
#
# Description:  Run Chrome performance tests using the Navigation API
#################################################

import sys
import os
import time
import csv
import json
import random
import subprocess
import select
import pprint
from optparse import OptionParser

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException


PAGE_WAIT_TIMEOUT=15


ToolParams = {
    'incognito_opt': '--incognito',
    'headless_opt': '--headless',
    'nogpu_opt': '--disable_gpu',
    'perf_timeings_out_file': '/tmp/perf_timings.out',
    'error_out_file': '/tmp/perf_timings.error'
}


class PerfTimings:

    def __init__(self):

        self.url = ""
        self.calc_timings = {}


    def print_metrics(self):

        pt_keys = self.calc_timings.keys()

        if len(pt_keys):
            pt_keys.sort()


        print
        print "==========================================================================================================="
        print "|               URL              |   DNS Res.   |   TCP Conn.  | Backend Time | Frontend Time | Page Load |"
        print "==========================================================================================================="
        print "| {url:30.25} | {DNS Resolution:9d} ms | {TCP Connection:9d} ms | {Backend Time:9d} ms | {Frontend Time:10d} ms | {Page Load:6d} ms |".format(**self.calc_timings)

        print "==========================================================================================================="



    def collect_perf_timings(self, url):

        self.url = url
        self.calc_timings.clear()

        current_url = self.url

        chrome_options = Options()

        # add option to start Chrome in Incognito mode
        # comment this line if you want to test normal Chrome mode
        chrome_options.add_argument("--incognito")

        driver = webdriver.Chrome(chrome_options=chrome_options)

        # set page load time out to 60 seconds
        driver.set_page_load_timeout(60)


        # Short routine to verify if the document is fully loaded
        def document_ready(driver):
            test = "return document.readyState"
            try:
                result = driver.execute_script(test)
                if result == "complete":
                    return True
                else:
                    return False
            except WebDriverException, e:
                return False


        try:
            # Get the URL and wait until the document is in complete state
            # This is particularly useful in case of redirections as the get would
            # return without having the final page fully loaded
            driver.get(current_url)
            wait = WebDriverWait(driver, PAGE_WAIT_TIMEOUT).until(document_ready)

        except TimeoutException, e:
            # If there's a timeout still follow to collect the metrics
            pass

         # Pull the performance timing data
        tmp_perf_timings = driver.execute_script("return window.performance.timing")
        tmp_perf_timings['url'] = str(current_url)

        # Caculate the timers
        self.calc_timers(tmp_perf_timings)

        # Close selenium WebDriver and return True
        driver.quit()
        return True


    def calc_timers(self, tmp_perf_timings):

        if len(tmp_perf_timings) == 0:
            return

        tmp_cal_timings = dict()

        tmp_cal_timings["url"] = tmp_perf_timings["url"].strip()
        tmp_cal_timings["DNS Resolution"] = tmp_perf_timings["domainLookupEnd"] - \
            tmp_perf_timings["domainLookupStart"]
        tmp_cal_timings["TCP Connection"] = tmp_perf_timings["connectEnd"] - \
            tmp_perf_timings["connectStart"]
        if tmp_perf_timings["secureConnectionStart"] > 0:
            tmp_cal_timings["SSL Handshake"] = tmp_perf_timings["connectEnd"] - \
            tmp_perf_timings["secureConnectionStart"]
        tmp_cal_timings["DOM Loading"] = tmp_perf_timings["domLoading"] - \
            tmp_perf_timings["navigationStart"]
        tmp_cal_timings["DOM Ready"] = tmp_perf_timings["domComplete"] - \
            tmp_perf_timings["navigationStart"]
        tmp_cal_timings["Page Load"] = tmp_perf_timings["loadEventEnd"] - \
            tmp_perf_timings["navigationStart"]
        tmp_cal_timings["Backend Time"] = tmp_perf_timings["responseStart"] - \
            tmp_perf_timings["navigationStart"]
        tmp_cal_timings["Frontend Time"] = tmp_perf_timings["loadEventEnd"] - \
            tmp_perf_timings["responseStart"]

        #pp = pprint.PrettyPrinter(indent=4)
        #pp.pprint(tmp_cal_timings)

        self.calc_timings = tmp_cal_timings


    def run(self, url):

        if self.collect_perf_timings(url):
            #print self.calc_timings
            self.print_metrics()


if __name__ == "__main__":

    parser = OptionParser(
        usage="Usage: {0} --file=<urls> [--iterations=<iterations>]".format(_FileName))
    parser.add_option("-f", "--file", dest="url_file",
                      help="input file with URLs list")
    parser.add_option("-n", "--iterations", dest="iterations",
                      help="Number of iterations", default='1')
    parser.add_option("-v", "--verbose", dest="verbose", action = 'store_true',
                      help="include additional SSL and DOM timers", default=False)

    (options, args) = parser.parse_args()

    if not options.url_file:   # if filename is not given
      parser.error('Filename not given')

    try:
        with open(options.url_file, 'r') as url_file:
           test_urls = url_file.readlines()
    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)
        exit(2)
    except:
        print "Unexpected error:", sys.exc_info()[0]
        exit(3)


    pt = PerfTimings()

    # randomly shuffle list of urls to avoid order bias in testing
    random.shuffle(test_urls)

    if options.iterations == '1':
       for i, url in enumerate(test_urls):
           pt.run(url)
    else:
        for x in range(0, int(options.iterations)):
            for i, url in enumerate(test_urls):
                pt.run(url)

    exit(0)
