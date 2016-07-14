# -*- coding: utf-8 -*-

import os
import urllib2

from sys import stdout, stderr


class Downloader:

    def __init__(self, reporter, directory=None):
        self.reporter = reporter
        self.directory = directory

    def save(self, url):
        try:
            self.reporter.progress("Downloading " + url, pad=True)
            remote_file = urllib2.urlopen(url)
            filename = os.path.basename(url)
            path = Downloader.resolve_path(self.directory, filename)
            with open(path, "wb") as local_file:
                local_file.write(remote_file.read())
                self.reporter.line("OK")
        except urllib2.HTTPError, ex:
            self.reporter.line("FAILED")
            self.reporter.error_line(ex.reason)
        except urllib2.URLError, ex:
            self.reporter.line("FAILED")
            self.reporter.error_line(ex.reason)

    @classmethod
    def resolve_path(cls, directory, filename):
        return filename if directory is None else os.path.join(directory, filename)
