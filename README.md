# vk-dialogue-export.py
## VKontakte Dialogue Exporter

A tool to export dialogue with specific interlocutor or chat.

## USAGE

Run the `create-auth-ini.py` script to generate the authentication file template and run:

```
python vk-dialogue-export.py chat_id
```

where `chat_id` is an interlocutor ID or a chat ID.

### COMMAND LINE ARGUMENTS

```
usage: vk-dialogue-export.py [-h] [--save-photos]
                             [--output-directory OUTPUT_DIRECTORY]
                             chat_id

positional arguments:
  chat_id               chat id

optional arguments:
  -h, --help            show this help message and exit
  --save-photos         save photos
  --output-directory OUTPUT_DIRECTORY
                        output directory
```

### NOTES

Script uses [https://github.com/dzhioev/vk_api_auth](https://github.com/dzhioev/vk_api_auth) to simplify business with OAuth.
