# -*- coding: utf-8 -*-

import datetime


class MessageWriter:

    def __init__(self, out, downloader, resolve_user, save_photos=False):
        self.out = out
        self.downloader = downloader
        self.resolve_user = resolve_user
        self.save_photos = save_photos

    def write(self, who, message):
        user_details = self.resolve_user(who)
        self.__write_message(message, user_details)
        if "fwd_messages" in message:
            self.__write_forwarded_messages(
                "<", enumerate(message["fwd_messages"]))
        if "attachments" in message:
            self.__write_attachments("+", enumerate(message["attachments"]))
        if "geo" in message:
            self.__write_geo(message["geo"])
        self.out.write("\n\n")

    def __write_message(self, message, user_details):
        self.out.write("[%s] %s:\n %s\n" % (
            MessageWriter.__format_timestamp(int(message["date"])),
            "%s %s" % (user_details["first_name"], user_details["last_name"]),
            MessageWriter.__normalize_message_body(message["body"])
        ))

    def __write_forwarded_messages(self, prefix, messages):
        for (i, msg) in messages:
            fwd_user_details = self.resolve_user(msg["uid"])
            self.out.write("Fwd(%s): %s (%s) %s\n" % (
                msg["uid"],
                "%s %s" % (
                    fwd_user_details[
                        "first_name"], fwd_user_details["last_name"]),
                self.__format_timestamp(int(msg["date"])),
                self.__normalize_message_body(msg["body"])
            ))

    def __write_attachments(self, prefix, attachments):
        for (i, attachment) in attachments:
            if attachment["type"] == "audio":
                self.__write_audio_attachment(prefix, attachment["audio"])
            elif attachment["type"] == "doc":
                self.__write_doc_attachment(prefix, attachment["doc"])
            elif attachment["type"] == "photo":
                self.__write_photo_attachment(prefix, attachment["photo"])
            elif attachment["type"] == "poll":
                self.__write_poll_attachment(prefix, attachment["poll"])
            elif attachment["type"] == "sticker":
                self.__write_sticker_attachment(prefix, attachment["sticker"])
            elif attachment["type"] == "video":
                self.__write_video_attachment(prefix, attachment["video"])
            elif attachment["type"] == "wall":
                self.__write_wall_attachment(prefix, attachment["wall"])
            else:
                raise Exception(
                    "unknown attachment type " + attachment["type"])

    def __write_audio_attachment(self, prefix, audio):
        self.out.write("%sAudio: %s - %s\n" %
                       (prefix, audio["artist"], audio["title"]))

    def __write_doc_attachment(self, prefix, doc):
        if "thumb" in doc:
            self.out.write("%sDoc: %s %s %s\n" %
                           (prefix, doc["title"], doc["url"], doc["thumb"]))
        else:
            self.out.write("%sDoc: %s %s\n" %
                           (prefix, doc["title"], doc["url"]))

    def __write_photo_attachment(self, prefix, photo):
        self.out.write("%sPhoto: %s %s\n" %
                       (prefix, photo["src_big"], photo["text"]))
        if self.save_photos:
            self.downloader.save(photo["src_big"])

    def __write_poll_attachment(self, prefix, poll):
        self.out.write("%sPoll: %s\n" % (prefix, poll["question"]))

    def __write_sticker_attachment(self, prefix, sticker):
        self.out.write("%sSticker: %s\n" %
                       (prefix, sticker[MessageWriter.__detect_largest_photo(sticker)]))

    def __write_video_attachment(self, prefix, video):
        self.out.write("%sVideo: %s\n" % (prefix, video["title"]))

    def __write_wall_attachment(self, prefix, wall):
        self.out.write("%sWall: %s\n" % (prefix, wall["text"]))
        if "attachments" in wall:
            self.__write_attachments(
                prefix + ">", enumerate(wall["attachments"]))

    def __write_geo(self, geo):
        if geo["type"] == "point":
            self.out.write("Geo: %s (%s)\n" %
                           (geo["place"]["title"], geo["coordinates"]))
        else:
            raise Exception("unknown geo type " + geo["type"])

    @classmethod
    def __format_timestamp(cls, timestamp):
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    @classmethod
    def __normalize_message_body(cls, body):
        return body.replace('<br>', '\n')

    @classmethod
    def __detect_largest_photo(cls, obj):
        def get_photo_keys():
            for k, v in obj.iteritems():
                if k.startswith("photo_"):
                    yield k[len("photo_"):]
        return "photo_%s" % max(map(lambda k: int(k), get_photo_keys()))
