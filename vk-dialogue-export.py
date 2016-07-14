# -*- coding: utf-8 -*-

import codecs
import datetime
import json
import os
import sys
import urllib2
from urllib import urlencode

from config import read_config
from downloader import Downloader
from memoize import Memoize
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

def format_timestamp(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def normalize_message_body(body):
    return body.replace('<br>', '\n')

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

def write_message(who, message):
    user_details = resolve_uid_details(who)
    out.write(u'[{date}] {full_name}:\n {message}\n'.format(**{
            'date': format_timestamp(int(message["date"])),

            'full_name': '%s %s' % (
                user_details["first_name"], user_details["last_name"]),

            'message': normalize_message_body(message["body"])
        }
    ))
    def write_forwarded_messages(prefix, messages):
        for (i, msg) in messages:
            fwd_user_details = resolve_uid_details(msg["uid"])
            out.write("Fwd(%s): %s (%s) %s\n" % (
                msg["uid"],
                "%s %s" % (fwd_user_details["first_name"], fwd_user_details["last_name"]),
                format_timestamp(int(msg["date"])),
                normalize_message_body(msg["body"])
            ))
    def write_attachments(prefix, attachments):
        def detect_largest_photo(obj):
            def get_photo_keys():
                for k, v in obj.iteritems():
                    if k.startswith("photo_"):
                        yield k[len("photo_"):]
            return "photo_%s" % max(map(lambda k: int(k), get_photo_keys()))
        for (i, attachment) in attachments:
             if attachment["type"] == "audio":
                 audio = attachment["audio"]
                 out.write("%sAudio: %s - %s\n" % (prefix, audio["artist"], audio["title"]))
             elif attachment["type"] == "doc":
                 doc = attachment["doc"]
                 if "thumb" in doc:
                     out.write("%sDoc: %s %s %s\n" % (prefix, doc["title"], doc["url"], doc["thumb"]))
                 else:
                     out.write("%sDoc: %s %s\n" % (prefix, doc["title"], doc["url"]))
             elif attachment["type"] == "photo":
                 photo = attachment["photo"]
                 out.write("%sPhoto: %s %s\n" % (prefix, photo["src_big"], photo["text"]))
                 if config["export"]["save_photos"]:
                     downloader.save(photo["src_big"])
             elif attachment["type"] == "poll":
                 poll = attachment["poll"]
                 out.write("%sPoll: %s" % (prefix, poll["question"]))
             elif attachment["type"] == "sticker":
                 sticker = attachment["sticker"]
                 out.write("%sSticker: %s\n" % (prefix, sticker[detect_largest_photo(sticker)]))
             elif attachment["type"] == "video":
                 video = attachment["video"]
                 out.write("%sVideo: %s\n" % (prefix, video["title"]))
             elif attachment["type"] == "wall":
                 wall = attachment["wall"]
                 out.write("%sWall: %s\n" % (prefix, wall["text"]))
                 if "attachments" in wall:
                     write_attachments(prefix + ">", enumerate(wall["attachments"]))
             else:
                 raise Exception("unknown attachment type " + attachment["type"])
    def write_geo(geo):
        if geo["type"] == "point":
            out.write("Geo: %s (%s)\n" % (geo["place"]["title"], geo["coordinates"]))
        else:
            raise Exception("unknown geo type " + geo["type"])
    if "fwd_messages" in message:
        write_forwarded_messages("<", enumerate(message["fwd_messages"]))
    if "attachments" in message:
        write_attachments("+", enumerate(message["attachments"]))
    if "geo" in message:
        write_geo(message["geo"])
    out.write("\n\n")


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
            write_message(message_part[i]["uid"], message_part[i])
    except IndexError:
        break

    result = mess + max_part
    if result > cnt:
        result = (mess - cnt) + mess
    mess = result
    reporter.line("Exported %s messages of %s" % (mess, cnt))

out.close()
reporter.line('Export done!')
