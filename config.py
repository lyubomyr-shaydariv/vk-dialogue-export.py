# -*- coding: utf-8 -*-

import ConfigParser

from argparse import ArgumentParser


def read_config():
    CLParser = ArgumentParser()
    CLParser.add_argument('chat_id', type=str, help='chat id')
    CLParser.add_argument(
        '--save-photos', dest='save_photos', action='store_true', help="save photos")
    CLParser.add_argument(
        '--output-directory', dest="output_directory", default=None, help="output directory")
    CLParser.add_argument(
        '--auto-output-directory', dest='auto_output_directory',
        action='store_true', help="generate output directory automatically")
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
            "output_directory": cmd_args.output_directory if not cmd_args.auto_output_directory else cmd_args.chat_id,
            "auto_output_directory": cmd_args.auto_output_directory
        },
        "auth": {
            "username": AuthConfig.get("auth", "username"),
            "password": AuthConfig.get("auth", "password"),
        },
        "app": {
            "id": Config.get("application", "app_id")
        }
    }
