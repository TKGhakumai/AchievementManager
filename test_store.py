import sqlite3
import tempfile
import unittest
from pathlib import Path
from achievement_core.store import AchievementStore, ValidationError

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.db'
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE achievements (achievement_id TEXT PRIMARY KEY)')
            db.execute("INSERT INTO achievements VALUES ('v06_first_comment')")
        self.store = AchievementStore(self.path)
        self.store.initialize()

    def tearDown(self):
        self.tmp.cleanup()

    def test_crud_and_legacy_untouched(self):
        data = {'title':'おしゃべり好き','rank':2,'operator':'AND',
                'conditions':[{'event_type':'chat.comment','target':100}]}
        aid = self.store.create(data)
        self.assertEqual(self.store.list_all()[0]['id'], aid)
        data['title'] = 'コメント職人'
        self.store.update(aid, data)
        self.assertEqual(self.store.list_all()[0]['title'], 'コメント職人')
        self.store.disable(aid)
        self.assertFalse(self.store.list_all()[0]['enabled'])
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM achievements').fetchone()[0], 1)

    def test_invalid_conditions(self):
        with self.assertRaises(ValidationError):
            self.store.create({'title':'NG','conditions':[{'event_type':'chat.comment','target':0}]})
        with self.assertRaises(ValidationError):
            self.store.create({'title':'NG','conditions':[{'event_type':'effect.glass','target':1}]})

if __name__ == '__main__':
    unittest.main()
