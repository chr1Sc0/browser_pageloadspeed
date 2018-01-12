#!/usr/bin/env python
"""Use environment Python variable."""
#################################################
#
# Description:  Run Chrome performance tests using the Navigation API
#################################################
import sys
import os
import time
import csv
import random
import pprint
from optparse import OptionParser


from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException, TimeoutException


PAGE_WAIT_TIMEOUT = 15
_FileName = "ff_loadtest.py"
csv_columns = ["url", "run", "DNS Resolution", "TCP Connection",
               "SSL Handshake", "Backend Time", "DOM Loading",
               "DOM Ready", "Frontend Time", "Page Load"]

ToolParams = {
    'incognito_opt': '--incognito',
    'headless_opt': '--headless',
    'nogpu_opt': '--disable_gpu',
    'perf_timings_out_file': '/tmp/perf_timings.out',
    'error_out_file': '/tmp/perf_timings.error'
}


class PerfTimings(object):
    """Collects Peformance Timings for a set of URLs."""

    def __init__(self):
        """Doc string."""
        self.current_url = ""
        self.test_urls = []
        self.calc_timings = {}

    def results_to_output_file(self, csv_filename):
        """Write performance timings collected to a CSV file."""
        if os.path.exists(csv_filename):
            # append_write = 'a' # append if already exists
            with open(csv_filename, 'a') as results_file:
                csvwriter = csv.DictWriter(
                    results_file, fieldnames=csv_columns)
                csvwriter.writerow(self.calc_timings)

        else:
            # append_write = 'w' # make a new file if not
            with open(csv_filename, 'wb') as results_file:
                csvwriter = csv.DictWriter(
                    results_file, fieldnames=csv_columns)
                csvwriter.writeheader()
                csvwriter.writerow(self.calc_timings)

    @classmethod
    def print_header(cls):
        """Print the header columns to stdout."""
        print "=" * 123
        header = "|               URL              |   DNS Res.   |"
        header += "   TCP Conn.  | SSL Handshake | Backend Time |"
        header += " Frontend Time | Page Load |"
        print header
        print "=" * 123

    def print_output(self):
        """Print performance timers for each URL to stdout."""
        print "| {url:30.25} | {DNS Resolution:9d} ms | {TCP Connection:9d} ms | {SSL Handshake:9d} ms  | {Backend Time:9d} ms | {Frontend Time:10d} ms | {Page Load:6d} ms |".format(**self.calc_timings)

        print "=" * 123

    def collect_navigation_timings(self, url, run_number):
        """
        Run the chromedriver to collect theperformance timers.

        For the received url, start the chroeme driver and calls Javascript to
        retrieve the navigation timing data ince the url has been loaded.

        """
        self.current_url = url
        self.calc_timings.clear()

        ff_options = Options()

        ff_binary = '/Applications/Firefox.app/Contents/MacOS/firefox'
        ff_options.add_argument("-private")

        driver = webdriver.Firefox(
            firefox_options=ff_options, firefox_binary=ff_binary)

        # set page load time out to 60s
        driver.set_page_load_timeout(30)

        # Short routine to verify if the document is fully loaded
        def doc_ready(driver):
            """Check readyState value for the page."""
            try:
                result = driver.execute_script("return document.readyState")
                return True if (result == "complete") else False

            except WebDriverException:
                return False

        try:
            # Get the URL and wait until the document is in complete state
            # This is particularly useful in case of redirections as the get
            # would return without having the final page fully loaded
            driver.get(self.current_url)
            WebDriverWait(driver, PAGE_WAIT_TIMEOUT).until(doc_ready)
        except TimeoutException:
            # If there's a timeout still follow to collect the metrics
            pass
        except WebDriverException:
            print "Could not open page for {0}".format(self.current_url)
            return False

        # Pull the performance timing data
        tmp_nav_timings = driver.execute_script(
            "return window.performance.timing")
        tmp_nav_timings['url'] = str(self.current_url).strip()
        tmp_nav_timings['run'] = str(run_number).strip()

        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(tmp_nav_timings)

        # Caculate the timers
        self.calc_timers(tmp_nav_timings)

        # Close selenium WebDriver and return True
        driver.quit()
        return True

    def calc_timers(self, tmp_nav_timings):
        """Calculate the navigation timings.

        From the the raw  performance timers for each page, does basic math to
        match the peformance timings.
        """
        if not tmp_nav_timings:
            return

        tmp_timings = dict()

        tmp_timings["url"] = tmp_nav_timings["url"]
        tmp_timings["run"] = tmp_nav_timings["run"]
        tmp_timings["DNS Resolution"] = tmp_nav_timings["domainLookupEnd"] - \
            tmp_nav_timings["domainLookupStart"]
        tmp_timings["TCP Connection"] = tmp_nav_timings["connectEnd"] - \
            tmp_nav_timings["connectStart"]
        if tmp_nav_timings["secureConnectionStart"] > 0:
            tmp_timings["SSL Handshake"] = tmp_nav_timings["connectEnd"] - \
                tmp_nav_timings["secureConnectionStart"]
        else:
            tmp_timings["SSL Handshake"] = 0
        if tmp_nav_timings["domLoading"] > 0:
            tmp_timings["DOM Loading"] = tmp_nav_timings["domLoading"] - \
                tmp_nav_timings["navigationStart"]
        else:
            tmp_timings["DOM Loading"] = "N/A"
        if tmp_nav_timings["domComplete"] > 0:
            tmp_timings["DOM Ready"] = tmp_nav_timings["domComplete"] - \
                tmp_nav_timings["navigationStart"]
        else:
            tmp_timings["DOM Ready"] = "N/A"
        tmp_timings["Page Load"] = tmp_nav_timings["loadEventEnd"] - \
            tmp_nav_timings["navigationStart"]
        tmp_timings["Backend Time"] = tmp_nav_timings["responseStart"] - \
            tmp_nav_timings["navigationStart"]
        tmp_timings["Frontend Time"] = tmp_nav_timings["loadEventEnd"] - \
            tmp_nav_timings["responseStart"]

        self.calc_timings = tmp_timings

    def run(self, test_urls, iterations, csv_output):
        """Run for each url the collection of performane timings.

        This is the main method exposed for the PerfTimings class

        Return:
        Nothing.

        Args:
        test_urls from the input file with URLS to test
        iterations: Number of iterations to do for each URL
        csv_output: Optional arg to write output to csv file.

        """
        self.test_urls = test_urls

        if not csv_output:
            self.print_header()
            if iterations == '1':
                for url in self.test_urls:
                    if self.collect_navigation_timings(url, 0):
                        self.print_output()
                    else:
                        continue
            else:
                for x in range(0, int(iterations)):
                    for url in self.test_urls:
                        if self.collect_navigation_timings(url, x):
                            self.print_output()
                        else:
                            continue
        else:
            # define unique results file for this run_number
            ts = int(time.time())
            filename = "perftimings_firefox_" + str(ts) + ".csv"
            if iterations == '1':
                for url in self.test_urls:
                    if self.collect_navigation_timings(url, 0):
                        self.results_to_output_file(filename)
                    else:
                        continue
            else:
                for x in range(0, int(iterations)):
                    for url in self.test_urls:
                        if self.collect_navigation_timings(url, x):
                            self.results_to_output_file(filename)
                        else:
                            continue


if __name__ == "__main__":

    parser = OptionParser(
        usage="Usage: {0} --file=<urls> \
               [--iterations=<iterations>]".format(_FileName))
    parser.add_option("-f", "--file",
                      dest="url_file",
                      help="input file with URLs list")
    parser.add_option("-n",
                      "--iterations",
                      dest="iterations",
                      help="Number of iterations",
                      default='1')
    parser.add_option("-v", "--verbose",
                      dest="verbose",
                      action='store_true',
                      help="include additional SSL and DOM timers",
                      default=False)
    parser.add_option("--csv",
                      dest="csv",
                      action='store_true',
                      help="write output to CSV file",
                      default=False)

    (options, args) = parser.parse_args()

    if not options.url_file:   # if filename is not given
        parser.error('Filename not given')

    try:
        with open(options.url_file, 'r') as url_file:
            urls = url_file.readlines()
    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)
        exit(2)
    except Exception:
        print "Unexpected error:", sys.exc_info()[0]
        exit(3)

    pt = PerfTimings()

    # randomly shuffle list of urls to avoid order bias in testing
    random.shuffle(urls)

    try:
        pt.run(urls, options.iterations, options.csv)

    except ValueError as e:
        print "ValueError Exception ocurred"

    exit(0)
