"""Standalone v0.8 achievement editor preview; does not modify v0.7 runtime."""
import sys
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox,
    QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget)
from achievement_core.store import AchievementStore, ValidationError

TEMPLATES = [
    ('コメント回数', 'chat.comment', 'おしゃべり好き', 100),
    ('スタンプ使用', 'chat.emote', 'スタンプマスター', 50),
    ('キーワード発言', 'chat.keyword', '合言葉を見つけた！', 1),
    ('チャネポ利用', 'channel_points.used', 'ポイントデビュー', 1),
]
EVENTS = [('コメント', 'chat.comment'), ('スタンプ', 'chat.emote'),
          ('キーワード', 'chat.keyword'), ('チャネポ', 'channel_points.used')]

class Editor(QWidget):
    def __init__(self, database):
        super().__init__()
        self.store = AchievementStore(database)
        self.store.initialize()
        self.current_id = None
        self.setWindowTitle('Achievement Manager v0.8 — 実績エディター（単体テスト）')
        self.resize(850, 680)
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel('保存済み実績'))
        self.items = QListWidget()
        self.items.currentRowChanged.connect(self.select_item)
        left.addWidget(self.items)
        fresh = QPushButton('新規作成')
        fresh.clicked.connect(self.new_item)
        left.addWidget(fresh)
        root.addLayout(left, 1)
        right = QVBoxLayout()
        form = QFormLayout()
        self.template = QComboBox()
        for label, _, _, _ in TEMPLATES:
            self.template.addItem(label)
        self.template.currentIndexChanged.connect(self.apply_template)
        form.addRow('テンプレート', self.template)
        self.title = QLineEdit()
        self.title.setMaxLength(80)
        form.addRow('実績名', self.title)
        self.description = QTextEdit()
        self.description.setMaximumHeight(75)
        form.addRow('説明', self.description)
        self.rank = QSpinBox()
        self.rank.setRange(1, 5)
        form.addRow('ランク ★', self.rank)
        self.event = QComboBox()
        for label, code in EVENTS:
            self.event.addItem(label, code)
        self.event.currentIndexChanged.connect(self.update_keyword_state)
        form.addRow('基本条件', self.event)
        self.count = QSpinBox()
        self.count.setRange(1, 10000)
        form.addRow('必要回数', self.count)
        self.keyword = QLineEdit()
        self.keyword.setMaxLength(100)
        form.addRow('キーワード', self.keyword)
        self.enabled = QCheckBox('実績を有効にする')
        self.enabled.setChecked(True)
        form.addRow('', self.enabled)
        right.addLayout(form)
        self.details = QGroupBox('詳細設定（クリックして展開）')
        self.details.setCheckable(True)
        self.details.setChecked(False)
        advanced = QFormLayout(self.details)
        self.extra = QCheckBox('追加条件を使用')
        advanced.addRow(self.extra)
        self.operator = QComboBox()
        self.operator.addItems(['AND', 'OR'])
        advanced.addRow('組み合わせ', self.operator)
        self.extra_event = QComboBox()
        for label, code in EVENTS:
            self.extra_event.addItem(label, code)
        self.extra_event.currentIndexChanged.connect(self.update_keyword_state)
        advanced.addRow('追加条件', self.extra_event)
        self.extra_count = QSpinBox()
        self.extra_count.setRange(1, 10000)
        advanced.addRow('追加条件の回数', self.extra_count)
        self.extra_keyword = QLineEdit()
        self.extra_keyword.setMaxLength(100)
        advanced.addRow('追加条件キーワード', self.extra_keyword)
        right.addWidget(self.details)
        buttons = QHBoxLayout()
        save = QPushButton('保存')
        save.clicked.connect(self.save)
        disable = QPushButton('無効化')
        disable.clicked.connect(self.disable)
        buttons.addWidget(save)
        buttons.addWidget(disable)
        right.addLayout(buttons)
        right.addWidget(QLabel('※ v0.8試験機能：保存と編集のみ対応。実績解除判定には未接続です。'))
        right.addStretch()
        root.addLayout(right, 2)
        self.refresh()
        self.new_item()

    def update_keyword_state(self, *_):
        self.keyword.setEnabled(self.event.currentData() == 'chat.keyword')
        self.extra_keyword.setEnabled(self.extra_event.currentData() == 'chat.keyword')

    def apply_template(self, index):
        if index < 0:
            return
        _, event, title, count = TEMPLATES[index]
        self.title.setText(title)
        self.event.setCurrentIndex(next(i for i in range(self.event.count()) if self.event.itemData(i) == event))
        self.count.setValue(count)
        self.keyword.clear()
        self.update_keyword_state()

    def new_item(self):
        self.current_id = None
        self.items.blockSignals(True)
        self.items.clearSelection()
        self.items.setCurrentRow(-1)
        self.items.blockSignals(False)
        self.description.clear()
        self.rank.setValue(1)
        self.enabled.setChecked(True)
        self.extra.setChecked(False)
        self.details.setChecked(False)
        self.operator.setCurrentText('AND')
        self.extra_count.setValue(1)
        self.extra_keyword.clear()
        self.apply_template(self.template.currentIndex())

    def refresh(self, selected=None):
        self.rows = self.store.list_all()
        self.items.blockSignals(True)
        self.items.clear()
        for item in self.rows:
            self.items.addItem(('' if item['enabled'] else '[無効] ') + item['title'])
        self.items.blockSignals(False)
        if selected:
            for i, item in enumerate(self.rows):
                if item['id'] == selected:
                    self.items.setCurrentRow(i)
                    break

    def select_item(self, index):
        if index < 0 or index >= len(self.rows):
            return
        data = self.rows[index]
        self.current_id = data['id']
        self.title.setText(data['title'])
        self.description.setPlainText(data['description'])
        self.rank.setValue(data['rank'])
        self.enabled.setChecked(data['enabled'])
        self.operator.setCurrentText(data['operator'])
        first = data['conditions'][0]
        self.set_condition(self.event, self.count, self.keyword, first)
        more = len(data['conditions']) > 1
        self.details.setChecked(more)
        self.extra.setChecked(more)
        if more:
            self.set_condition(self.extra_event, self.extra_count, self.extra_keyword, data['conditions'][1])
        self.update_keyword_state()

    @staticmethod
    def set_condition(combo, spin, field, condition):
        idx = combo.findData(condition['event_type'])
        if idx >= 0:
            combo.setCurrentIndex(idx)
        spin.setValue(condition['target'])
        field.setText(condition.get('keyword', ''))

    @staticmethod
    def condition(combo, spin, field):
        result = {'event_type': combo.currentData(), 'target': spin.value()}
        if combo.currentData() == 'chat.keyword':
            result['keyword'] = field.text()
        return result

    def save(self):
        conditions = [self.condition(self.event, self.count, self.keyword)]
        if self.extra.isChecked():
            conditions.append(self.condition(self.extra_event, self.extra_count, self.extra_keyword))
        data = {'title': self.title.text(), 'description': self.description.toPlainText(),
                'rank': self.rank.value(), 'enabled': self.enabled.isChecked(),
                'operator': self.operator.currentText(), 'conditions': conditions}
        try:
            if self.current_id:
                self.store.update(self.current_id, data)
                identifier = self.current_id
            else:
                identifier = self.store.create(data)
            self.refresh(identifier)
            QMessageBox.information(self, '保存完了', '実績を保存しました。')
        except (ValidationError, KeyError) as exc:
            QMessageBox.warning(self, '入力エラー', str(exc))

    def disable(self):
        if not self.current_id:
            QMessageBox.information(self, '確認', '無効化する実績を左側から選択してください。')
            return
        if QMessageBox.question(self, '確認', 'この実績を無効化しますか？') != QMessageBox.Yes:
            return
        self.store.disable(self.current_id)
        self.refresh(self.current_id)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    db = Path(__file__).resolve().parent / 'v08_editor_demo.sqlite3'
    editor = Editor(db)
    editor.show()
    sys.exit(app.exec_())
