# -*- coding: utf-8 -*-

import codecs
import ConfigParser
import datetime
import json
import sys
import urllib2
from urllib import urlencode

import vk_auth


def _api(method, params, token):
    params.append(("access_token", token))
    url = "https://api.vk.com/method/%s?%s" % (method, urlencode(params))
    return json.loads(urllib2.urlopen(url).read())["response"]

# read config values

AuthConfig = ConfigParser.ConfigParser()
if len(AuthConfig.read(".auth.ini")) != 1:
    sys.exit("Can't read .auth.ini")

Config = ConfigParser.ConfigParser()
if len(Config.read("config.ini")) != 1:
    sys.exit("Can't read config.ini")

username = AuthConfig.get("auth", "username")
password = AuthConfig.get("auth", "password")

messages_id = Config.get("messages", "chat_id")
messages_type = Config.get("messages", "chat_type")

app_id = Config.get("application", "app_id")

# some chat preparation

if messages_type == "interlocutor":
    is_chat = False
elif messages_type == "chat":
    is_chat = True
else:
    sys.exit("Messages type must be either interlocutor or chat.")


# auth to get token

try:
    token, user_id = vk_auth.auth(username, password, app_id, 'messages')
except RuntimeError:
    sys.exit("Incorrect username/password. Please check it.")

sys.stdout.write('Authorized vk\n')

# get some information about chat

selector = "chat_id" if is_chat else "uid"
messages = _api("messages.getHistory", [(selector, messages_id)], token)

out = codecs.open(
    'vk_exported_dialogue_%s%s.txt' % ('ui' if not is_chat else 'c', messages_id),
    "w+", "utf-8"
)

human_uids = [messages[1]["uid"]]

# Export uids from dialogue.
# Due to vk.api, start from 1.
for i in range(1, 100):
    try:
        if messages[i]["uid"] != human_uids[0]:
            human_uids.append(messages[i]["uid"])
    except IndexError:
        pass

# Export details from uids
human_details = _api(
    "users.get",
    [("uids", ','.join(str(v) for v in human_uids))],
    token
)

human_details_index = {}
for human_detail in human_details:
    human_details_index[human_detail["uid"]] = human_detail

def write_message(who, to_write):
    out.write(u'[{date}] {full_name}:\n {message}\n'.format(**{
            'date': datetime.datetime.fromtimestamp(
                int(to_write["date"])).strftime('%Y-%m-%d %H:%M:%S'),

            'full_name': '%s %s' % (
                human_details_index[who]["first_name"], human_details_index[who]["last_name"]),

            'message': to_write["body"].replace('<br>', '\n')
        }
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
    if "attachments" in to_write:
        write_attachments("+", enumerate(to_write["attachments"]))
    out.write("\n\n")


mess = 0
max_part = 200  # Due to vk.api

cnt = messages[0]
sys.stdout.write("Count of messages: %s\n" % cnt)

while mess != cnt:
    # Try to retrieve info anyway

    while True:
        try:
            message_part = _api(
                "messages.getHistory",
                [(selector, messages_id), ("offset", mess), ("count", max_part), ("rev", 1)],
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
