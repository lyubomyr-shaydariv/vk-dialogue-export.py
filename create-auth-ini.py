# -*- coding: utf-8 -*-

from getpass import getpass
from sys import stdin, stdout

auth_file_path = ".auth.ini"

stdout.write("Enter your VK username: ")
username = stdin.readline().strip()

stdout.write("Enter your VK password: ")
password = getpass("").strip()

with open(auth_file_path, 'a') as auth_file:
    auth_file.write("[auth]\n")
    auth_file.write("username = %s\n" % username)
    auth_file.write("password = %s\n" % password)

print "%s generated" % auth_file_path
print "Please do NOT forget to delete %s when you're done with export!" % auth_file_path
