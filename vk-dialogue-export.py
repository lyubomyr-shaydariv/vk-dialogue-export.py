# -*- coding: utf-8 -*-

import codecs
import json
import os
import sys
import urllib2
from urllib import urlencode

from config import read_config
from downloader import Downloader
from memoize import Memoize
from messages import MessageWriter
from reporter import Reporter
import vk_auth


def _api(method, params, token):
    params.append(("access_token", token))
    url = "https://api.vk.com/method/%s?%s" % (method, urlencode(params))
    payload = urllib2.urlopen(url).read()
    payload_json = json.loads(payload)
    if not "response" in payload_json:
        sys.exit("Request failed:\nURL     = %s\nPAYLOAD = %s" % (url, payload))
    return payload_json["response"]

config = read_config()
reporter = Reporter.std_reporter()
downloader = Downloader(reporter, directory=config["export"]["output_directory"])

# auth to get token

try:
    reporter.progress("Authenticating as %s" % config["auth"]["username"], pad=True)
    token, user_id = vk_auth.auth(config["auth"]["username"], config["auth"]["password"], config["app"]["id"], 'messages')
    reporter.line("OK")
except RuntimeError:
    reporter.line("FAILED")
    sys.exit("Cannot authenticate, please check your credentials in .auth.ini")

# get some information about chat

selector = "chat_id" if config["export"]["is_group_chat"] else "uid"
messages = _api("messages.getHistory", [(selector, config["export"]["chat_id"])], token)

# prepare output

if config["export"]["output_directory"] is not None:
    if not os.path.exists(config["export"]["output_directory"]):
        os.makedirs(config["export"]["output_directory"])
output_filename = 'vk_exported_dialogue_%s%s.txt' % ('ui' if not config["export"]["is_group_chat"] else 'c', config["export"]["chat_id"])
output_path = Downloader.resolve_path(config["export"]["output_directory"], output_filename)
out = codecs.open(output_path, "w+", "utf-8")

def resolve_uid_details(uid):
    return _api("users.get", [("user_ids", uid)], token)[0]

resolve_uid_details = Memoize(resolve_uid_details)

message_writer = MessageWriter(out, downloader, lambda uid: resolve_uid_details(uid), save_photos=config["export"]["save_photos"])

mess = 0
max_part = 200  # Due to vk.api

cnt = messages[0]
reporter.line("Message count: %s" % cnt)

while mess != cnt:
    # Try to retrieve info anyway

    while True:
        try:
            message_part = _api(
                "messages.getHistory",
                [(selector, config["export"]["chat_id"]), ("offset", mess), ("count", max_part), ("rev", 1)],
                token
            )
        except Exception as e:
            reporter.error_line('Got error %s, continue...' % e)
            continue
        break

    try:
        for i in range(1, 201):
            message_writer.write(message_part[i]["uid"], message_part[i])
    except IndexError:
        break

    result = mess + max_part
    if result > cnt:
        result = (mess - cnt) + mess
    mess = result
    reporter.line("Exported %s messages of %s" % (mess, cnt))

out.close()
reporter.line('Export done!')
