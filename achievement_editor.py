"""Achievement Manager v0.8 editor — staged edits and explicit persistence."""
import json
from pathlib import Path
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
    QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QSpinBox,
    QComboBox, QCheckBox, QGroupBox, QScrollArea)
from achievement_core.store import AchievementStore, ValidationError

TEMPLATES = [('コメント回数','chat.comment','おしゃべり好き',100),
             ('スタンプ使用','chat.emote','スタンプマスター',50),
             ('キーワード発言','chat.keyword','合言葉を見つけた！',1),
             ('チャネポ利用','channel_points.used','ポイントデビュー',1)]
EVENTS = [('コメント','chat.comment'),('スタンプ','chat.emote'),
          ('キーワード','chat.keyword'),('チャネポ','channel_points.used')]

class Editor(QWidget):
    saved = pyqtSignal()
    def __init__(self, database):
        super().__init__()
        self.store = AchievementStore(database)
        self.store.initialize()
        self.current_id = None
        self._loading = False
        self._baseline = None
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel('保存済み実績'))
        self.items = QListWidget()
        self.items.setMinimumWidth(185)
        self.items.setMaximumWidth(275)
        self.items.currentRowChanged.connect(self.select_item)
        left.addWidget(self.items)
        self.new_button = QPushButton('新規作成')
        self.new_button.clicked.connect(self.new_item)
        left.addWidget(self.new_button)
        root.addLayout(left, 1)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
        panel = QWidget(); right = QVBoxLayout(panel)
        self.heading = QLabel('新しい実績を作成')
        self.heading.setStyleSheet('font-size: 16px; font-weight: bold;')
        right.addWidget(self.heading)
        form = QFormLayout()
        self.template = QComboBox()
        for label,_,_,_ in TEMPLATES: self.template.addItem(label)
        self.template.currentIndexChanged.connect(self.apply_template)
        form.addRow('テンプレート',self.template)
        self.title = QLineEdit(); self.title.setMaxLength(80)
        form.addRow('実績名',self.title)
        self.rank = QComboBox()
        for n in range(1,6): self.rank.addItem('★'*n+'☆'*(5-n),n)
        form.addRow('★ ランク',self.rank)
        self.event = QComboBox()
        for label,code in EVENTS: self.event.addItem(label,code)
        self.event.currentIndexChanged.connect(self.update_keyword_state)
        form.addRow('基本条件',self.event)
        self.count = QSpinBox(); self.count.setRange(1,10000)
        form.addRow('達成回数',self.count)
        self.keyword = QLineEdit(); self.keyword.setMaxLength(100)
        form.addRow('キーワード',self.keyword)
        self.enabled = QCheckBox('実績を有効にする'); self.enabled.setChecked(True)
        form.addRow('',self.enabled)
        right.addLayout(form)
        self.details = QGroupBox('特殊条件（Beta） — クリックして展開')
        self.details.setCheckable(True); self.details.setChecked(False)
        advanced = QFormLayout(self.details)
        self.extra = QCheckBox('追加条件を使用')
        advanced.addRow(self.extra)
        self.operator = QComboBox(); self.operator.addItems(['AND','OR'])
        advanced.addRow('条件の組み合わせ',self.operator)
        self.extra_event = QComboBox()
        for label,code in EVENTS: self.extra_event.addItem(label,code)
        self.extra_event.currentIndexChanged.connect(self.update_keyword_state)
        advanced.addRow('追加条件',self.extra_event)
        self.extra_count = QSpinBox(); self.extra_count.setRange(1,10000)
        advanced.addRow('追加条件の達成回数',self.extra_count)
        self.extra_keyword = QLineEdit(); self.extra_keyword.setMaxLength(100)
        advanced.addRow('追加条件キーワード',self.extra_keyword)
        self.advanced_widgets = [self.extra,self.operator,self.extra_event,self.extra_count,self.extra_keyword]
        self.details.toggled.connect(self._toggle_details)
        self.extra.toggled.connect(self._toggle_details)
        right.addWidget(self.details)
        self.note = QLabel('入力した変更は「新規追加」または「変更を保存」を押すまで保存されません。')
        self.note.setWordWrap(True); right.addWidget(self.note)
        buttons=QHBoxLayout()
        self.save_button=QPushButton('新規追加'); self.save_button.clicked.connect(self.save)
        self.clear_button=QPushButton('クリア'); self.clear_button.clicked.connect(self.clear_form)
        self.disable_button=QPushButton('無効化'); self.disable_button.clicked.connect(self.disable)
        buttons.addWidget(self.save_button); buttons.addWidget(self.clear_button); buttons.addWidget(self.disable_button)
        right.addLayout(buttons); right.addStretch()
        scroll.setWidget(panel); root.addWidget(scroll,3)
        for widget,signal in [(self.title,self.title.textChanged),(self.keyword,self.keyword.textChanged),
            (self.extra_keyword,self.extra_keyword.textChanged),(self.count,self.count.valueChanged),
            (self.extra_count,self.extra_count.valueChanged),(self.rank,self.rank.currentIndexChanged),
            (self.event,self.event.currentIndexChanged),(self.extra_event,self.extra_event.currentIndexChanged),
            (self.operator,self.operator.currentIndexChanged),(self.extra,self.extra.toggled),
            (self.enabled,self.enabled.toggled)]:
            signal.connect(self._update_dirty)
        self.refresh(); self._reset_form()

    def _toggle_details(self,*_):
        # Hide contents rather than merely disabling them.
        expanded=self.details.isChecked()
        for w in self.advanced_widgets: w.setVisible(expanded and (w is self.extra or self.extra.isChecked()))
        layout=self.details.layout()
        for i in range(layout.rowCount()):
            label=layout.itemAt(i,QFormLayout.LabelRole)
            if label and label.widget(): label.widget().setVisible(expanded and self.extra.isChecked())
        self._update_dirty()

    def update_keyword_state(self,*_):
        self.keyword.setVisible(self.event.currentData()=='chat.keyword')
        label=self._label_for(self.keyword)
        if label: label.setVisible(self.keyword.isVisible())
        self.extra_keyword.setEnabled(self.extra_event.currentData()=='chat.keyword')
        self._update_dirty()

    def _label_for(self,widget):
        layout=self.keyword.parentWidget().layout() if self.keyword.parentWidget() else None
        # QFormLayout is in panel's top-level layout.
        for child in self.findChildren(QLabel):
            if child.text()=='キーワード': return child
        return None

    def apply_template(self,index):
        if index<0 or self._loading:return
        _,ev,title,count=TEMPLATES[index]
        self.title.setText(title)
        self.event.setCurrentIndex(self.event.findData(ev))
        self.count.setValue(count); self.keyword.clear()
        self.update_keyword_state()

    def _snapshot(self):
        return {'title':self.title.text(),'rank':self.rank.currentData(),
                'enabled':self.enabled.isChecked(),'operator':self.operator.currentText(),
                'conditions':[self._condition(self.event,self.count,self.keyword)]+
                    ([self._condition(self.extra_event,self.extra_count,self.extra_keyword)] if self.extra.isChecked() else [])}

    @staticmethod
    def _condition(combo,spin,keyword):
        d={'event_type':combo.currentData(),'target':spin.value()}
        if combo.currentData()=='chat.keyword':d['keyword']=keyword.text()
        return d

    def has_unsaved_changes(self):
        return self._baseline is not None and self._snapshot()!=self._baseline

    def _update_dirty(self,*_):
        if self._loading or self._baseline is None:return
        self.heading.setText(('実績を編集' if self.current_id else '新しい実績を作成')+('  ● 未保存' if self.has_unsaved_changes() else ''))

    def confirm_discard(self):
        if not self.has_unsaved_changes():return True
        return QMessageBox.question(self,'未保存の変更があります',
            '実績の設定が保存されていません。\n変更を破棄して移動しますか？\n\n「いいえ」で編集を続けます。',
            QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes

    def _reset_form(self):
        self._loading=True
        self.current_id=None
        self.items.blockSignals(True); self.items.setCurrentRow(-1); self.items.blockSignals(False)
        self.template.setCurrentIndex(0); self.title.setText(TEMPLATES[0][2])
        self.rank.setCurrentIndex(0); self.event.setCurrentIndex(0); self.count.setValue(100)
        self.keyword.clear(); self.enabled.setChecked(True)
        self.extra.setChecked(False); self.details.setChecked(False)
        self.operator.setCurrentText('AND'); self.extra_event.setCurrentIndex(0)
        self.extra_count.setValue(1); self.extra_keyword.clear()
        self._loading=False
        self._toggle_details(); self.update_keyword_state()
        self.save_button.setText('新規追加'); self.disable_button.setEnabled(False)
        self._baseline=self._snapshot(); self._update_dirty()

    def new_item(self):
        if not self.confirm_discard():return
        self._reset_form()

    def clear_form(self):
        if not self.confirm_discard():return
        if self.current_id:
            self._load_item(next(x for x in self.rows if x['id']==self.current_id))
        else:self._reset_form()

    def refresh(self,selected=None):
        self.rows=self.store.list_all()
        self.items.blockSignals(True); self.items.clear()
        for item in self.rows:self.items.addItem(('' if item['enabled'] else '[無効] ')+item['title'])
        if selected:
            for i,item in enumerate(self.rows):
                if item['id']==selected:self.items.setCurrentRow(i);break
        self.items.blockSignals(False)

    def select_item(self,index):
        if self._loading or index<0 or index>=len(self.rows):return
        if not self.confirm_discard():
            self.items.blockSignals(True)
            old=next((i for i,r in enumerate(self.rows) if r['id']==self.current_id),-1)
            self.items.setCurrentRow(old); self.items.blockSignals(False)
            return
        self._load_item(self.rows[index])

    def _load_item(self,data):
        self._loading=True
        self.current_id=data['id']
        self.items.blockSignals(True)
        idx=next((i for i,r in enumerate(self.rows) if r['id']==self.current_id),-1)
        self.items.setCurrentRow(idx); self.items.blockSignals(False)
        self.title.setText(data['title']); self.rank.setCurrentIndex(data['rank']-1)
        self.enabled.setChecked(data['enabled']); self.operator.setCurrentText(data['operator'])
        self._set_condition(self.event,self.count,self.keyword,data['conditions'][0])
        self.template.setCurrentIndex(max(0,next((i for i,x in enumerate(TEMPLATES) if x[1]==data['conditions'][0]['event_type']),0)))
        more=len(data['conditions'])>1
        self.extra.setChecked(more); self.details.setChecked(more)
        if more:self._set_condition(self.extra_event,self.extra_count,self.extra_keyword,data['conditions'][1])
        self._loading=False; self._toggle_details(); self.update_keyword_state()
        self.save_button.setText('変更を保存'); self.disable_button.setEnabled(data['enabled'])
        self._baseline=self._snapshot(); self._update_dirty()

    @staticmethod
    def _set_condition(combo,spin,field,c):
        idx=combo.findData(c['event_type'])
        if idx>=0:combo.setCurrentIndex(idx)
        spin.setValue(c['target']); field.setText(c.get('keyword',''))

    def save(self):
        data=self._snapshot(); data['description']=''
        try:
            if self.current_id:
                self.store.update(self.current_id,data); identifier=self.current_id
            else:identifier=self.store.create(data)
            self.refresh(identifier)
            self._load_item(next(x for x in self.rows if x['id']==identifier))
            self.saved.emit()
            QMessageBox.information(self,'保存完了','実績を保存しました。実績一覧と個人実績カードに反映されます。')
        except (ValidationError,KeyError,ValueError) as exc:
            QMessageBox.warning(self,'入力エラー',str(exc))

    def disable(self):
        if not self.current_id:return
        if not self.confirm_discard():return
        if QMessageBox.question(self,'無効化','この実績を無効化しますか？',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        self.store.disable(self.current_id)
        self.refresh(self.current_id)
        self._load_item(next(x for x in self.rows if x['id']==self.current_id))
        self.saved.emit()

if __name__=='__main__':
    import sys
    app=QApplication(sys.argv)
    w=Editor(Path(__file__).resolve().parent/'v08_editor_demo.sqlite3'); w.show()
    sys.exit(app.exec_())
