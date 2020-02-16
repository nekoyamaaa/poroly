"""部屋番号とクエスト内容を投稿してください。掲示板サーバーへの書き込みが完了するとボットがリアクション{reaction}をつけてリプライでもお知らせします。部屋番号は半角数字でお願いします。
例)
1234567 真ミド
0987654 アギト練習
3458765 黄金周回"""

import re

ROOM_REGEX = re.compile(
    r'^(?P<id>\d{3}[-]?\d{4})\s*(?P<message>.*)$', re.ASCII
)

class Validator:
    def user_validate(self, data):
        """Validate data dict.  Basic attributes (owner, guild and time)
        are validated in base class"""
        cleaned = {}
        cleaned['id'] = str(data.get('id') or "").replace('-', '')
        if len(cleaned['id']) != 7 or not cleaned['id'].isdigit():
            raise ValueError('id must be 7 length digits.')

        return cleaned

class Parser:
    def user_notification(self, action, obj=None):
        """Message to user on each actions.
        If returned value is falsey, no messages will be sent"""
        if action == "saved":
            return (
                "書き込みました\n"
                "ID: `{id}` / コメント: `{msg}`"
            ).format(id=obj['id'], msg=obj.get('message', '(なし)'))

    def parse_content(self, content, message=None):
        """Parse message content and return game-specific info"""
        matched = ROOM_REGEX.search(content)
        if not matched:
            return None
        matched = matched.groupdict()
        matched['id'] = matched['id'].replace('-', '')
        return matched
