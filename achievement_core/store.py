"""v0.8 achievement definition repository; intentionally isolated from v0.7 runtime.

Existing achievements/progress/event_counters are not modified by this module.
Call initialize() with a SQLite connection (or path) before CRUD operations.
"""
import json
import re
import sqlite3
import uuid
from pathlib import Path

EVENT_TYPES = frozenset({
    'chat.comment', 'chat.emote', 'chat.keyword', 'channel_points.used',
    'effect.passing', 'effect.meteor', 'effect.flash', 'effect.glass',
    'effect.smoke', 'hacking.used', 'hacking.giant', 'hacking.swarm',
    'passing.giant', 'passing.fireworks',
})
TKG_EVENTS = frozenset(x for x in EVENT_TYPES if x.startswith(('effect.', 'hacking.', 'passing.')))
MAX_CONDITIONS = 5
MAX_TARGET = 10000

class ValidationError(ValueError):
    pass

def validate(data):
    if not isinstance(data, dict):
        raise ValidationError('実績データはオブジェクトで指定してください')
    title = data.get('title')
    description = data.get('description', '')
    rank = data.get('rank', 1)
    conditions = data.get('conditions')
    operator = data.get('operator', 'AND')
    enabled = data.get('enabled', True)
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 80:
        raise ValidationError('実績名は1〜80文字で入力してください')
    if not isinstance(description, str) or len(description) > 500:
        raise ValidationError('説明は500文字以内です')
    if type(rank) is not int or not 1 <= rank <= 5:
        raise ValidationError('ランクは1〜5の整数です')
    if operator not in ('AND', 'OR'):
        raise ValidationError('組み合わせはANDまたはORです')
    if type(enabled) is not bool:
        raise ValidationError('enabledは真偽値です')
    if not isinstance(conditions, list) or not 1 <= len(conditions) <= MAX_CONDITIONS:
        raise ValidationError('条件は1〜5個です')
    clean = []
    for item in conditions:
        if not isinstance(item, dict):
            raise ValidationError('条件の形式が不正です')
        event = item.get('event_type')
        target = item.get('target')
        keyword = item.get('keyword', '')
        if event not in EVENT_TYPES:
            raise ValidationError('対応していないイベントです: ' + str(event))
        if type(target) is not int or not 1 <= target <= MAX_TARGET:
            raise ValidationError('回数は1〜10000の整数です')
        if not isinstance(keyword, str) or len(keyword) > 100:
            raise ValidationError('キーワードは100文字以内です')
        if event == 'chat.keyword' and not keyword.strip():
            raise ValidationError('キーワード条件には文字列が必要です')
        if event != 'chat.keyword' and keyword:
            raise ValidationError('キーワードはchat.keywordでのみ使用できます')
        condition = {'event_type': event, 'target': target}
        if event == 'chat.keyword':
            condition['keyword'] = keyword.strip()
        if condition in clean:
            raise ValidationError('同じ条件を重複登録できません')
        clean.append(condition)
    return {'title': title.strip(), 'description': description, 'rank': rank,
            'operator': operator, 'conditions': clean, 'enabled': enabled}

class AchievementStore:
    def __init__(self, database):
        self.database = str(database)

    def _connect(self):
        db = sqlite3.connect(self.database)
        db.row_factory = sqlite3.Row
        return db

    def initialize(self):
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS v08_achievement_definitions (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
                rank INTEGER NOT NULL CHECK(rank BETWEEN 1 AND 5),
                operator TEXT NOT NULL CHECK(operator IN ('AND','OR')),
                conditions_json TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'custom',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )''')

    def create(self, data, source='custom'):
        value = validate(data)
        if source not in ('custom', 'twitch_template', 'tkg_template'):
            raise ValidationError('sourceが不正です')
        if source != 'tkg_template' and any(c['event_type'] in TKG_EVENTS for c in value['conditions']):
            raise ValidationError('TKGイベントはTKG連携用テンプレートでのみ指定できます')
        identifier = 'v08_' + uuid.uuid4().hex
        with self._connect() as db:
            db.execute('''INSERT INTO v08_achievement_definitions
                (id,title,description,rank,operator,conditions_json,enabled,source)
                VALUES(?,?,?,?,?,?,?,?)''',
                (identifier, value['title'], value['description'], value['rank'],
                 value['operator'], json.dumps(value['conditions'], ensure_ascii=False),
                 int(value['enabled']), source))
        return identifier

    def list_all(self):
        with self._connect() as db:
            rows = db.execute('SELECT * FROM v08_achievement_definitions ORDER BY created_at,id').fetchall()
        return [self._decode(row) for row in rows]

    @staticmethod
    def _decode(row):
        item = dict(row)
        item['conditions'] = json.loads(item.pop('conditions_json'))
        item['enabled'] = bool(item['enabled'])
        return item

    def update(self, identifier, data):
        value = validate(data)
        with self._connect() as db:
            row = db.execute('SELECT source FROM v08_achievement_definitions WHERE id=?', (identifier,)).fetchone()
            if row is None:
                raise KeyError(identifier)
            if row['source'] != 'tkg_template' and any(c['event_type'] in TKG_EVENTS for c in value['conditions']):
                raise ValidationError('TKGイベントはTKG連携用テンプレートでのみ指定できます')
            db.execute('''UPDATE v08_achievement_definitions SET title=?,description=?,rank=?,
                operator=?,conditions_json=?,enabled=?,updated_at=CURRENT_TIMESTAMP WHERE id=?''',
                (value['title'],value['description'],value['rank'],value['operator'],
                 json.dumps(value['conditions'],ensure_ascii=False),int(value['enabled']),identifier))

    def disable(self, identifier):
        """Soft delete; retain definition for future progress-history compatibility."""
        with self._connect() as db:
            cur = db.execute('UPDATE v08_achievement_definitions SET enabled=0,updated_at=CURRENT_TIMESTAMP WHERE id=?', (identifier,))
            if cur.rowcount == 0:
                raise KeyError(identifier)
