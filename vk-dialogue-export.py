# -*- coding: utf-8 -*-

import argparse
import codecs
import ConfigParser
import datetime
import json
import os
import sys
import urllib2
from urllib import urlencode

from memoize import Memoize
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

def build_output_path(directory, filename):
    return filename if directory is None else os.path.join(directory, filename)

# read config values

def read_config():
    CLParser = argparse.ArgumentParser()
    CLParser.add_argument('chat_id', type=str, help='chat id')
    CLParser.add_argument('--save-photos', dest='save_photos', action='store_true', help="save photos")
    CLParser.add_argument('--output-directory', dest="output_directory", default=None, help="output directory")
    cmd_args = CLParser.parse_args()

    AuthConfig = ConfigParser.ConfigParser()
    if len(AuthConfig.read(".auth.ini")) != 1:
        sys.exit("Can't read .auth.ini")

    Config = ConfigParser.ConfigParser()
    if len(Config.read("config.ini")) != 1:
        sys.exit("Can't read config.ini")

    is_group_chat = cmd_args.chat_id.startswith("c")

    return {
        "export": {
            "chat_id": cmd_args.chat_id if not is_group_chat else cmd_args.chat_id[1:],
            "is_group_chat": is_group_chat,
            "save_photos": cmd_args.save_photos,
            "output_directory": cmd_args.output_directory
        },
        "auth": {
            "username": AuthConfig.get("auth", "username"),
            "password": AuthConfig.get("auth", "password"),
        },
        "app": {
            "id": Config.get("application", "app_id")
        }
    }

config = read_config()

# auth to get token

try:
    sys.stdout.write("Authenticating as %s...\n" % config["auth"]["username"])
    token, user_id = vk_auth.auth(config["auth"]["username"], config["auth"]["password"], config["app"]["id"], 'messages')
    sys.stdout.write("Success!\n")
except RuntimeError:
    sys.exit("Cannot authenticate, please check your credentials in .auth.ini")

# get some information about chat

selector = "chat_id" if config["export"]["is_group_chat"] else "uid"
messages = _api("messages.getHistory", [(selector, config["export"]["chat_id"])], token)

# prepare output

if not os.path.exists(config["export"]["output_directory"]):
    os.makedirs(config["export"]["output_directory"])
output_filename = 'vk_exported_dialogue_%s%s.txt' % ('ui' if not config["export"]["is_group_chat"] else 'c', config["export"]["chat_id"])
output_path = build_output_path(config["export"]["output_directory"], output_filename)
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
                     try:
                         sys.stdout.write("Downloading %s... " % photo["src_big"])
                         remote_file = urllib2.urlopen(photo["src_big"])
                         with open(build_output_path(config["export"]["output_directory"], os.path.basename(photo["src_big"])), "wb") as local_file:
                             local_file.write(remote_file.read())
                         sys.stdout.write("OK\n")
                     except urllib2.HTTPError, ex:
                         sys.stdout.write("%s\n" % ex.reason)
                     except urllib2.URLError, ex:
                         sys.stdout.write("%s\n" % ex.reason)
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
sys.stdout.write("Message count: %s\n" % cnt)

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
            sys.stderr.write('Got error %s, continue...\n' % e)
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
    sys.stdout.write("Exported %s messages of %s\n" % (mess, cnt))

out.close()
sys.stdout.write('Export done!\n')
