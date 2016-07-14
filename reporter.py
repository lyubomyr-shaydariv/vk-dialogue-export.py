# -*- coding: utf-8 -*-

from sys import stdout, stderr


class Reporter:

    def __init__(self, out, err):
        self.out = out
        self.err = err

    @classmethod
    def std_reporter(cls):
        return Reporter(stdout, stderr)

    def line(self, message):
        self.out.write(message)
        self.out.write("\n")

    def progress(self, message, pad=False):
        self.out.write(message)
        self.out.write("...")
        if pad:
            self.out.write(" ")

    def error_line(self, message):
        self.err.write(message)
        self.err.write("\n")
