import os
import sys
import sqlite3
import shutil
import json
import threading
import wave
import math
import struct
import socket
import ssl
import re
import unicodedata
import secrets
import urllib.request
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from pathlib import Path

from PyQt5.QtCore import Qt, QSettings, QTimer, QUrl, QObject, pyqtSignal, QProcess
import twitch_oauth
import update_service
from achievement_editor import Editor as AchievementEditor
from achievement_core.store import AchievementStore
from achievement_core.sorting import sort_achievements
from PyQt5.QtGui import QColor, QPainter, QFont
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QMessageBox, QGroupBox, QFormLayout, QSpinBox,
    QCheckBox, QAbstractItemView, QProgressBar, QFileDialog, QSlider, QScrollArea)

BASE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'AchievementManager'
BASE.mkdir(parents=True, exist_ok=True)
DB_PATH = BASE / 'achievements.db'
BRIDGE_KEY_PATH = BASE / 'bridge_key.txt'
if not BRIDGE_KEY_PATH.exists():
    BRIDGE_KEY_PATH.write_text(secrets.token_urlsafe(32), encoding='utf-8')
BRIDGE_KEY = BRIDGE_KEY_PATH.read_text(encoding='utf-8').strip()


def public_client_id():
    """Public Twitch application Client ID, packaged with the application."""
    path = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'app_config.json'
    try:
        client_id = str(json.loads(path.read_text(encoding='utf-8')).get('twitch_client_id', '')).strip()
    except (OSError, ValueError):
        return ''
    return client_id if re.fullmatch(r'[a-z0-9]{20,40}', client_id) else ''


# ID, name, description, rank, event_type, target. v0.6 canonical 31 achievements.
ACHIEVEMENTS = [
 ('v06_first_comment','はじめまして！','初めてコメントする',1,'chat.comment',1),
 ('v06_questions','ハテナやめてね','? または ？ が3文字以上連続',2,'chat.questions',1),
 ('v06_laugh','草生えちまった','w/W（半角・全角）が3文字以上連続',1,'chat.laugh',1),
 ('v06_badgame','おい、まさかクソゲーってこのゲームのことを言ってるんじゃないよな？','クソゲー／く〇ゲー／くそげー／ク〇ゲーを含む',3,'chat.badgame',1),
 ('v06_tkg','それって・・・たまごかけごはん？！？！','TKGとコメントする',4,'chat.tkg',1),
 ('v06_kaomoji','顔文字いいよね','顔文字を含むコメントを送る',1,'chat.kaomoji',1),
 ('v06_greeting','挨拶ありがと！','おはよう／こんにちは／こんばんは／おはようございますを送る',1,'chat.greeting',1),
 ('v06_emote_1','スタンプデビュー','スタンプを初めて使用',1,'chat.emote',1),
 ('v06_emote_30','スタンプ職人','スタンプ累計30個',2,'chat.emote',30),
 ('v06_emote_50','スタンプラブ','スタンプ累計50個',2,'chat.emote',50),
 ('v06_emote_100','あるんだから使わないと','スタンプ累計100個',3,'chat.emote',100),
 ('v06_gg','グットゲーム！！','shirat43Gg スタンプを送信',1,'chat.gg',1),
 ('v06_effect_1','初めての妨害','指定5演出のいずれかを初めて使用',1,'effect.five',1),
 ('v06_effect_10','いたずら好き','指定5演出を合計10回使用',1,'effect.five',10),
 ('v06_effect_50','妨害の常習犯','指定5演出を合計50回使用',3,'effect.five',50),
 ('v06_glass_30','画面破壊職人','ガラス演出を累計30回使用',3,'effect.glass',30),
 ('v06_effect_200','妨害王','チャネポ演出を累計200回使用',4,'effect.used',200),
 ('v06_effect_1000','混沌の創造主','チャネポ演出を累計1000回使用',5,'effect.used',1000),
 ('v06_smoke_10','ヘビースモーカー','スモーク演出を累計10回使用',2,'effect.smoke',10),
 ('v06_hack_1','ハッキング入門','ハッキング初使用',1,'hacking.used',1),
 ('v06_hack_10','見習いハッカー','ハッキング累計10回',2,'hacking.used',10),
 ('v06_hack_50','熟練ハッカー','ハッキング累計50回',3,'hacking.used',50),
 ('v06_hack_200','画面侵略者','ハッキング累計200回',4,'hacking.used',200),
 ('v06_hack_giant_1','巨大化成功！','ハッキング巨大化レア初当選',3,'hacking.giant',1),
 ('v06_hack_giant_5','巨大化の申し子','ハッキング巨大化レア累計5回',4,'hacking.giant',5),
 ('v06_hack_swarm_1','デジタル大群','ハッキング60体レア初当選',4,'hacking.swarm',1),
 ('v06_hack_legend','伝説のハッカー','ハッキング巨大化と60体レアに各5回当選',5,'combo.hack',1),
 ('v06_pass_giant_1','でっかくなっちゃった！','通ります巨大化レア初当選',3,'passing.giant',1),
 ('v06_pass_giant_5','巨大化の達人','通ります巨大化レア累計5回',4,'passing.giant',5),
 ('v06_pass_fireworks_1','たーまやー！','通ります花火レア初当選',4,'passing.fireworks',1),
 ('v06_pass_fireworks_5','幸運すぎて怖い','通ります花火レア累計5回',5,'passing.fireworks',5),
]
# Legacy TKG-specific achievements remain in SQLite for historical compatibility.
# They are hidden unless the streamer explicitly enables the optional TKG bridge.
TKG_LEGACY_IDS = frozenset({
    'v06_tkg', 'v06_badgame', 'v06_gg',
    *(a[0] for a in ACHIEVEMENTS if a[4].startswith(('effect.', 'hacking.', 'passing.', 'combo.')))
})
GENERIC_ACHIEVEMENTS = tuple(a for a in ACHIEVEMENTS if a[0] not in TKG_LEGACY_IDS)

def visible_legacy_achievements():
    return [a for a in (ACHIEVEMENTS if BRIDGE_ENABLED else GENERIC_ACHIEVEMENTS)
            if a[0] not in V08_STORE.deleted_ids()]

def visible_v08_definitions(enabled_only=False):
    return [d for d in v08_definitions(enabled_only)
            if (BRIDGE_ENABLED or d['source'] != 'tkg_template')
            and d['id'] not in V08_STORE.deleted_ids()]

ACTIVE_IDS = tuple(a[0] for a in ACHIEVEMENTS)
FIVE_EFFECTS = ('effect.passing','effect.meteor','effect.flash','effect.glass','effect.smoke')
BRIDGE_ALLOWED = set(FIVE_EFFECTS) | {'effect.used','hacking.used','hacking.giant','hacking.swarm','passing.giant','passing.fireworks'}

COLORS = {1:'#429BEB',2:'#429BEB',3:'#ED5965',4:'#ED5965',5:'#E9BD55'}

def connect():
    con = sqlite3.connect(str(DB_PATH))
    con.execute('PRAGMA foreign_keys=ON')
    return con

def init_db():
    if DB_PATH.exists() and not (BASE / 'achievements.before_stage4.db').exists():
        with sqlite3.connect(str(DB_PATH)) as src, sqlite3.connect(str(BASE / 'achievements.before_stage4.db')) as dst:
            src.backup(dst)
    # Make an untouched backup before the first v0.6 schema migration.
    if DB_PATH.exists() and not (BASE / 'achievements.before_v06.db').exists():
        source = sqlite3.connect(str(DB_PATH))
        dest = sqlite3.connect(str(BASE / 'achievements.before_v06.db'))
        try: source.backup(dest)
        finally: dest.close(); source.close()
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, display_name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS achievements (
            achievement_id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
            rank INTEGER NOT NULL CHECK(rank BETWEEN 1 AND 5), event_type TEXT NOT NULL,
            target INTEGER NOT NULL, icon_path TEXT, stamp_path TEXT);
        CREATE TABLE IF NOT EXISTS progress (
            user_id TEXT NOT NULL, achievement_id TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0,
            unlocked_at TEXT, PRIMARY KEY(user_id,achievement_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(achievement_id) REFERENCES achievements(achievement_id));
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            achievement_id TEXT NOT NULL, occurred_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS event_counters (
            user_id TEXT NOT NULL, event_type TEXT NOT NULL, count INTEGER NOT NULL,
            PRIMARY KEY(user_id,event_type));
        CREATE TABLE IF NOT EXISTS v08_progress (user_id TEXT NOT NULL, achievement_id TEXT NOT NULL, unlocked_at TEXT NOT NULL, PRIMARY KEY(user_id,achievement_id));
        ''')
        for a in ACHIEVEMENTS:
            db.execute('''INSERT INTO achievements(achievement_id,title,description,rank,event_type,target)
                VALUES(?,?,?,?,?,?) ON CONFLICT(achievement_id) DO NOTHING''',a)

    V08_STORE.initialize()
    # Import existing Stage 3 drafts once, preserving their stable IDs.
    old=BASE/'achievements_v08_preview.db'
    if old.exists():
        with sqlite3.connect(str(old)) as source, connect() as dest:
            try:
                source.row_factory=sqlite3.Row
                for row in source.execute('SELECT * FROM v08_achievement_definitions'):
                    dest.execute("""INSERT OR IGNORE INTO v08_achievement_definitions
                        (id,title,description,rank,operator,conditions_json,enabled,source,created_at,updated_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?)""",tuple(row[k] for k in
                        ('id','title','description','rank','operator','conditions_json','enabled','source','created_at','updated_at')))
            except sqlite3.OperationalError:
                pass

def increment(db, uid, event_type, amount=1):
    db.execute('''INSERT INTO event_counters(user_id,event_type,count) VALUES(?,?,?)
        ON CONFLICT(user_id,event_type) DO UPDATE SET count=count+excluded.count''',(uid,event_type,amount))


# Stage 4: custom definitions share the existing runtime database with user/event history.
V08_STORE = AchievementStore(DB_PATH)

def v08_definitions(enabled_only=False):
    rows=V08_STORE.list_all()
    return [r for r in rows if r['enabled']] if enabled_only else rows

def v08_condition_count(db,uid,condition):
    kind=condition['event_type']
    if kind=='chat.keyword':
        kind='chat.keyword:'+unicodedata.normalize('NFKC',condition['keyword']).casefold()
    row=db.execute('SELECT count FROM event_counters WHERE user_id=? AND event_type=?',(uid,kind)).fetchone()
    return row[0] if row else 0

def v08_status(db,uid,definition):
    conditions=definition['conditions']
    counts=[v08_condition_count(db,uid,c) for c in conditions]
    targets=[c['target'] for c in conditions]
    met=[n>=t for n,t in zip(counts,targets)]
    achieved=all(met) if definition['operator']=='AND' else any(met)
    # For AND, show the least completed condition; for OR, the most completed one.
    ratio=(min if definition['operator']=='AND' else max)(min(n/t,1) for n,t in zip(counts,targets))
    return achieved,round(ratio*100),counts,targets

def v08_record(db,uid,keyword_message=None):
    if keyword_message is not None:
        normalized=unicodedata.normalize('NFKC',keyword_message).casefold()
        keywords={c['keyword'] for d in visible_v08_definitions(True) for c in d['conditions'] if c['event_type']=='chat.keyword'}
        for word in keywords:
            if unicodedata.normalize('NFKC',word).casefold() in normalized:
                increment(db,uid,'chat.keyword:'+unicodedata.normalize('NFKC',word).casefold())
    unlocked=[]
    for d in visible_v08_definitions(True):
        achieved,_,_,_=v08_status(db,uid,d)
        if not achieved:continue
        at=datetime.now().astimezone().isoformat(timespec='seconds')
        cur=db.execute('INSERT OR IGNORE INTO v08_progress(user_id,achievement_id,unlocked_at) VALUES(?,?,?)',(uid,d['id'],at))
        if cur.rowcount:
            db.execute('INSERT INTO event_log(user_id,achievement_id,occurred_at) VALUES(?,?,?)',(uid,d['id'],at))
            unlocked.append(d['title'])
    return unlocked

def record_event(user_id, name, event_type, amount=1, keyword_message=None):
    user_id = str(user_id).strip()
    name = str(name).strip()
    if not user_id or not name: raise ValueError('ユーザーIDと表示名を入力してください。')
    if event_type not in {a[4] for a in ACHIEVEMENTS} | set(FIVE_EFFECTS) | {'chat.emote','chat.keyword_message','channel_points.used'}:
        raise ValueError('不明なイベント: '+event_type)
    if not BRIDGE_ENABLED and (event_type.startswith(('effect.', 'hacking.', 'passing.', 'combo.'))):
        raise ValueError('TKG専用イベントはTKG接続時のみ記録できます。')
    amount = int(amount)
    if not 1 <= amount <= 100: raise ValueError('不正なイベント数')
    unlocked=[]
    with connect() as db:
        db.execute('INSERT INTO users(user_id,display_name) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name',(user_id,name))
        if event_type!='chat.keyword_message': increment(db,user_id,event_type,amount)
        if event_type in FIVE_EFFECTS: increment(db,user_id,'effect.five',amount)
        if event_type in ('hacking.giant','hacking.swarm'):
            giant=db.execute('SELECT count FROM event_counters WHERE user_id=? AND event_type=?',(user_id,'hacking.giant')).fetchone()
            swarm=db.execute('SELECT count FROM event_counters WHERE user_id=? AND event_type=?',(user_id,'hacking.swarm')).fetchone()
            if giant and swarm and giant[0]>=5 and swarm[0]>=5:
                # set once; combination progress is a boolean condition.
                db.execute('''INSERT INTO event_counters(user_id,event_type,count) VALUES(?,?,1)
                    ON CONFLICT(user_id,event_type) DO UPDATE SET count=1''',(user_id,'combo.hack'))
        allowed={a[0] for a in visible_legacy_achievements()}
        for aid,title,rank,kind,target in db.execute(
                'SELECT achievement_id,title,rank,event_type,target FROM achievements'):
            if aid not in allowed: continue
            row=db.execute('SELECT count FROM event_counters WHERE user_id=? AND event_type=?',(user_id,kind)).fetchone()
            count=row[0] if row else 0
            old=db.execute('SELECT unlocked_at FROM progress WHERE user_id=? AND achievement_id=?',(user_id,aid)).fetchone()
            at=datetime.now().astimezone().isoformat(timespec='seconds') if count>=target and not (old and old[0]) else None
            if count==0 and not old: continue
            db.execute('''INSERT INTO progress(user_id,achievement_id,count,unlocked_at) VALUES(?,?,?,?)
                ON CONFLICT(user_id,achievement_id) DO UPDATE SET count=excluded.count,
                unlocked_at=COALESCE(progress.unlocked_at,excluded.unlocked_at)''',(user_id,aid,count,at))
            if at:
                db.execute('INSERT INTO event_log(user_id,achievement_id,occurred_at) VALUES(?,?,?)',(user_id,aid,at))
                unlocked.append(title)
        unlocked.extend(v08_record(db,user_id,keyword_message))
    return unlocked


def parse_chat_events(message, emote_tags, target_emote_name="shirat43Gg"):
    normalized=unicodedata.normalize('NFKC',message)
    events=['chat.comment']
    if re.search(r'\?{3,}',normalized): events.append('chat.questions')
    if re.search(r'w{3,}',normalized,re.I): events.append('chat.laugh')
    if re.search(r'(?:クソゲー|く〇ゲー|くそげー|ク〇ゲー)',message): events.append('chat.badgame')
    if re.search(r'(?<![A-Za-z])TKG(?![A-Za-z])',normalized,re.I): events.append('chat.tkg')
    if re.search(r'(?:おはようございます|おはよう|こんにちは|こんばんは)',message): events.append('chat.greeting')
    # Conservative patterns; no promise of perfect kaomoji recognition.
    if re.search(r'[（(][^\s（）()]{1,24}[）)]',message) or re.search(r'[ಠ・´˘][_・ಠ´˘]{1,5}',message):
        events.append('chat.kaomoji')
    emote_count=0; gg=False
    target_emote_name = (target_emote_name or "").strip().casefold()
    utf16_units = message.encode("utf-16-le")
    # Twitch emotes tag: emote_id:start-end,start-end / ...
    for group in emote_tags.split('/'):
        if ':' not in group: continue
        emote_id,positions=group.split(':',1)
        for position in positions.split(','):
            if not re.fullmatch(r'\d+-\d+',position): continue
            emote_count+=1
            start,end=map(int,position.split('-'))
            # IRC indices are UTF-16 offsets. Twitch's tag identifies actual emotes.
            try: token=utf16_units[start*2:(end+1)*2].decode('utf-16-le')
            except UnicodeDecodeError: token=''
            if target_emote_name and token.casefold()==target_emote_name: gg=True
    if emote_count: events.append(('chat.emote',min(emote_count,100)))
    if gg: events.append('chat.gg')
    events.append(('chat.keyword_message',message))
    return events


# 通知は解除済みイベントのみ。ブラウザは読み取り専用で、カードを公開しません。
NOTIFICATIONS = []
NOTIFICATION_LOCK = threading.Lock()

# TKG → Achievement Manager のローカルイベント受付。HTTPスレッドからGUIを直接操作しない。
BRIDGE_SIGNAL = None
BRIDGE_TOKEN = None
BRIDGE_CLIENT_ID = None
BRIDGE_TOKEN_LOCK = threading.Lock()
BRIDGE_EVENT_IDS = set()
BRIDGE_EVENT_LOCK = threading.Lock()
BRIDGE_ENABLED = False  # Explicitly enabled only by the streamer
BRIDGE_PROTOCOL_VERSION = 1

class BridgeEmitter(QObject):
    received = pyqtSignal(str, str, str)
    status = pyqtSignal(str)

def resolve_twitch_user(login):
    """TwitchユーザーIDは表示名から推測せずHelix APIで取得する。"""
    with BRIDGE_TOKEN_LOCK:
        token, client_id = BRIDGE_TOKEN, BRIDGE_CLIENT_ID
    if not token or not client_id:
        return None
    url = 'https://api.twitch.tv/helix/users?login=' + urllib.parse.quote(login)
    req = urllib.request.Request(url, headers={'Authorization':'Bearer '+token,'Client-Id':client_id})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            users = json.load(response).get('data', [])
        return users[0] if users else None
    except Exception:
        return None

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/api/status':
            self.send_error(404); return
        if self.headers.get('X-Achievement-Key') != BRIDGE_KEY:
            self.reply(403, {'error':'unauthorized'}); return
        self.reply(200, {'app':'AchievementManager', 'protocol_version':BRIDGE_PROTOCOL_VERSION,
                         'connected':BRIDGE_ENABLED, 'supported_events':sorted(BRIDGE_ALLOWED)})

    def do_POST(self):
        if self.path != '/api/event':
            self.send_error(404); return
        if not BRIDGE_ENABLED:
            self.reply(503, {'error':'TKG connection is disabled'}); return
        if self.headers.get('X-Achievement-Key') != BRIDGE_KEY:
            self.send_error(403); return
        try:
            length = int(self.headers.get('Content-Length','0'))
            if length <= 0 or length > 4096: raise ValueError('invalid length')
            data = json.loads(self.rfile.read(length))
            event_type = data.get('event_type','')
            login = str(data.get('login','')).lower().strip()
            event_id = str(data.get('event_id',''))
            if event_type not in BRIDGE_ALLOWED:
                raise ValueError('invalid event_type')
            if not re.fullmatch(r'[a-z0-9_]{3,25}',login):
                raise ValueError('invalid login')
            if not 8 <= len(event_id) <= 100:
                raise ValueError('invalid event_id')
            with BRIDGE_EVENT_LOCK:
                if event_id in BRIDGE_EVENT_IDS:
                    self.reply(200,{'status':'duplicate'}); return
            user = resolve_twitch_user(login)
            if not user:
                self.reply(503,{'error':'Twitch user lookup unavailable. Connect Twitch chat first.'}); return
            with BRIDGE_EVENT_LOCK:
                if event_id in BRIDGE_EVENT_IDS:
                    self.reply(200,{'status':'duplicate'}); return
                BRIDGE_EVENT_IDS.add(event_id)
                if len(BRIDGE_EVENT_IDS)>10000: BRIDGE_EVENT_IDS.clear()
            BRIDGE_SIGNAL.received.emit(user['id'],user.get('display_name') or login,event_type)
            self.reply(202,{'status':'accepted'})
        except (ValueError, json.JSONDecodeError) as exc:
            self.reply(400,{'error':str(exc)})
        except Exception:
            self.reply(500,{'error':'internal error'})

    def reply(self,code,obj):
        body=json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass

class NotificationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/notifications'):
            with NOTIFICATION_LOCK:
                body=json.dumps(NOTIFICATIONS[-40:],ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
        elif self.path == '/' or self.path.startswith('/index.html'):
            body=OBS_HTML.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
        else:
            self.send_error(404); return
        self.send_header('Cache-Control','no-store')
        self.send_header('Access-Control-Allow-Origin','http://127.0.0.1:8766')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*args):
        pass

OBS_HTML = r"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
html,body{margin:0;background:transparent;font-family:'Yu Gothic UI',Meiryo,sans-serif;color:#fff;overflow:hidden}
#stack{position:absolute;right:22px;top:22px;width:460px;display:flex;flex-direction:column;gap:10px}
.toast{box-sizing:border-box;background:#142033f2;border:2px solid var(--color);border-radius:13px;padding:18px;box-shadow:0 10px 28px #0007;animation:enter .35s ease-out}
.tag{color:var(--color);font-size:12px;font-weight:bold;letter-spacing:1px}.name{font-size:22px;font-weight:bold;margin:6px 0}.stars{color:var(--color);font-size:18px}.user{font-size:14px;color:#e3e8f0}
@keyframes enter{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:translateX(0)}}
</style></head><body><div id="stack"></div><script>
let seen=new Set();let initialized=false;let queue=[];let showing=false;
const colors={1:'#429BEB',2:'#429BEB',3:'#ED5965',4:'#ED5965',5:'#E9BD55'};
function display(){if(showing||!queue.length)return;showing=true;let e=queue.shift();let n=document.createElement('div');n.className='toast';n.style.setProperty('--color',colors[e.rank]||colors[1]);
let tag=document.createElement('div');tag.className='tag';tag.textContent='🏆 ACHIEVEMENT UNLOCKED';n.append(tag);
let title=document.createElement('div');title.className='name';title.textContent=e.title;n.append(title);
let stars=document.createElement('div');stars.className='stars';stars.textContent='★'.repeat(e.rank)+'☆'.repeat(5-e.rank);n.append(stars);
let user=document.createElement('div');user.className='user';user.textContent=e.name+' さんが解除！';n.append(user);
document.getElementById('stack').append(n);setTimeout(()=>{n.remove();showing=false;display()},Math.max(2,e.duration)*1000)}
async function poll(){try{let r=await fetch('/api/notifications',{cache:'no-store'});let a=await r.json();for(let e of a){if(!seen.has(e.id)){seen.add(e.id);if(initialized)queue.push(e)}}initialized=true;display()}catch(e){}}
setInterval(poll,500);poll();
</script></body></html>"""

class Toast(QWidget):
    def __init__(self, title, name, rank, duration):
        super().__init__(None,Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool|Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground,True)
        self.setAttribute(Qt.WA_ShowWithoutActivating,True)
        self.rank=rank
        self.resize(450,145)
        screen=QApplication.primaryScreen().availableGeometry()
        self.move(screen.right()-self.width()-22,screen.top()+25)
        color=COLORS.get(rank,'#429BEB')
        self.setStyleSheet(f"""QFrame#toast {{ background-color: #172235; border: 2px solid {color}; border-radius: 12px; }}
            QLabel {{background:transparent; color:white;}}""")
        from PyQt5.QtWidgets import QFrame
        frame=QFrame(self); frame.setObjectName('toast');frame.setGeometry(0,0,450,145)
        layout=QVBoxLayout(frame);layout.setContentsMargins(20,14,20,14);layout.setSpacing(4)
        top=QLabel('🏆 ACHIEVEMENT UNLOCKED');top.setStyleSheet(f'color:{color};font-weight:bold;font-size:11pt;')
        title_label=QLabel(title);title_label.setStyleSheet('font-size:18pt;font-weight:bold;')
        stars=QLabel('★'*rank+'☆'*(5-rank));stars.setStyleSheet(f'color:{color};font-size:15pt;')
        viewer=QLabel(name+' さんが解除しました！')
        for item in (top,title_label,stars,viewer): layout.addWidget(item)
        QTimer.singleShot(max(2,duration)*1000,self.close)

def make_default_sound(path):
    if path.exists(): return
    rate=22050
    samples=[]
    # 著作権フリーの短い3音チャイムをコードで合成
    for frequency in (523.25,659.25,783.99):
        for i in range(int(rate*.15)):
            t=i/rate
            env=(1-t/.15)**1.6
            samples.append(int(9500*env*math.sin(2*math.pi*frequency*t)))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate)
        f.writeframes(struct.pack('<'+'h'*len(samples),*samples))

class OAuthEvents(QObject):
    success = pyqtSignal(str, str, str)
    failure = pyqtSignal(str)


class TwitchChatWorker(QObject):
    event_received = pyqtSignal(str, str, object)
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = False
        self.sock = None
        self.thread = None
        self.target_emote_name = "shirat43Gg"

    def start(self, channel, nick, token):
        self.stop()
        self.running = True
        self.thread = threading.Thread(target=self._run, args=(channel, nick, token), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        sock = self.sock
        self.sock = None
        if sock:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            try: sock.close()
            except OSError: pass

    def _run(self, channel, nick, token):
        try:
            with socket.create_connection(('irc.chat.twitch.tv', 6697), timeout=12) as raw:
                with ssl.create_default_context().wrap_socket(raw, server_hostname='irc.chat.twitch.tv') as sock:
                    self.sock = sock
                    sock.settimeout(2)
                    sock.sendall(('PASS oauth:' + token + '\r\n' +
                                  'NICK ' + nick + '\r\n' +
                                  'CAP REQ :twitch.tv/tags twitch.tv/commands\r\n' +
                                  'JOIN #' + channel + '\r\n').encode())
                    self.status_changed.emit('接続処理中…')
                    buffer = ''
                    while self.running:
                        try: data = sock.recv(8192)
                        except socket.timeout: continue
                        if not data: break
                        buffer += data.decode('utf-8', errors='replace')
                        while '\r\n' in buffer:
                            line, buffer = buffer.split('\r\n', 1)
                            if line.startswith('PING '):
                                sock.sendall(('PONG ' + line[5:] + '\r\n').encode())
                            elif ' 001 ' in line or ' JOIN #' in line:
                                self.status_changed.emit('接続中：#' + channel)
                            elif 'Login authentication failed' in line or 'Improperly formatted auth' in line:
                                raise RuntimeError('認証に失敗しました。トークンと権限を確認してください。')
                            elif ' PRIVMSG #' in line:
                                self._handle_message(line)
        except Exception as exc:
            if self.running:
                self.status_changed.emit('切断・エラー：' + str(exc))
        finally:
            self.sock = None
            self.running = False
            self.status_changed.emit('未接続')

    def _handle_message(self, line):
        tags = {}
        if line.startswith('@'):
            raw_tags, _, line = line.partition(' ')
            tags = dict(part.split('=', 1) if '=' in part else (part, '') for part in raw_tags[1:].split(';'))
        m = re.match(r':([^! ]+)!.*? PRIVMSG #[^ ]+ :(.*)$', line)
        if not m: return
        name = tags.get('display-name') or m.group(1)
        uid = tags.get('user-id')
        if not uid: return
        for ev in parse_chat_events(m.group(2),tags.get('emotes',''),self.target_emote_name):
            self.event_received.emit(uid,name,ev)


class UpdateEvents(QObject):
    checked = pyqtSignal(object, bool)
    failed = pyqtSignal(str, bool)
    downloaded = pyqtSignal(str)
    download_failed = pyqtSignal(str)
    progress = pyqtSignal(int)


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Achievement Manager v0.8 Beta.6')
        self.toasts=[]
        self.toast_queue=[]
        self.toast_busy=False
        self.notification_serial=0
        # Dashboard is a session view; never delete persistent event history.
        with connect() as db:
            self.dashboard_after_id=db.execute('SELECT COALESCE(MAX(id),0) FROM event_log').fetchone()[0]

        self.http_server=None
        self.bridge_server=None
        self.bridge_emitter=BridgeEmitter()
        self.bridge_emitter.received.connect(self.on_bridge_event)
        self.player=QMediaPlayer(self)
        self.default_sound=BASE/'default_unlock.wav'
        make_default_sound(self.default_sound)
        self.prefs = QSettings('AchievementManager', 'AchievementManager')
        self.oauth_events = OAuthEvents()
        self.oauth_events.success.connect(self.on_oauth_success)
        self.oauth_events.failure.connect(self.on_oauth_failure)
        self.oauth_busy = False
        self.update_events = UpdateEvents()
        self.update_events.checked.connect(self.on_update_checked)
        self.update_events.failed.connect(self.on_update_check_failed)
        self.update_events.downloaded.connect(self.on_update_downloaded)
        self.update_events.download_failed.connect(self.on_update_download_failed)
        self.update_events.progress.connect(self.on_update_progress)
        self.update_busy = False
        self.update_download_busy = False
        self.update_info = None
        self.resize(1040, 740)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.make_dashboard()
        self.make_achievements()
        self.make_profiles()
        self.make_v08_editor()
        self.make_settings()
        self.twitch_worker = TwitchChatWorker()
        self.twitch_worker.target_emote_name = str(self.prefs.value('gg_emote_name', 'shirat43Gg')).strip()
        self.twitch_worker.event_received.connect(self.on_twitch_event)
        self.twitch_worker.status_changed.connect(self.twitch_status.setText)
        self._last_tab_index=self.tabs.currentIndex()
        self._tab_guard=False
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.apply_theme()
        self.refresh_all()
        self.new_refresh_timer=QTimer(self)
        self.new_refresh_timer.setInterval(30000)
        self.new_refresh_timer.timeout.connect(self.refresh_card)
        self.new_refresh_timer.start()
        self.start_obs_server()
        # Never block startup; user must approve any installation.
        QTimer.singleShot(2500, lambda: self.check_for_updates(False))
        # TKG bridge stays OFF until the user explicitly enables it.

    def make_v08_editor(self):
        # Separate database: v0.7 achievements and progress are not modified.
        self.v08_editor = AchievementEditor(DB_PATH, legacy_provider=lambda: {a[0] for a in visible_legacy_achievements()})
        self.v08_editor.saved.connect(self.refresh_all)
        self.v08_editor.setWindowTitle('実績管理')
        self.tabs.addTab(self.v08_editor, '実績管理（v0.8）')

    def page(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(14); lay.setContentsMargins(22,22,22,22)
        return w,lay

    def table(self, headers):
        t = QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        return t

    def fill(self, table, rows):
        table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,value in enumerate(row):
                item = QTableWidgetItem(str(value) if value is not None else '')
                if isinstance(value,str) and value.startswith('★'):
                    item.setForeground(__import__('PyQt5.QtGui',fromlist=['QColor']).QColor(COLORS.get(value.count('★'),'#FFFFFF')))
                table.setItem(i,j,item)

    def make_dashboard(self):
        w,l=self.page()
        self.stats=QLabel(); self.stats.setStyleSheet('font-size:17pt;font-weight:bold;')
        l.addWidget(QLabel('ダッシュボード')); l.addWidget(self.stats)
        history_bar=QHBoxLayout()
        history_bar.addWidget(QLabel('起動後の実績解除ログ'))
        history_bar.addStretch()
        clear_history=QPushButton('ログをクリア')
        clear_history.clicked.connect(self.clear_dashboard_log)
        history_bar.addWidget(clear_history)
        l.addLayout(history_bar)
        self.recent=self.table(['日時','視聴者','実績']); l.addWidget(self.recent)
        self.tabs.addTab(w,'ダッシュボード')

    def make_achievements(self):
        w,l=self.page(); l.addWidget(QLabel('実績一覧（既存実績 + カスタム実績）'))
        bar=QHBoxLayout(); bar.addWidget(QLabel('★ ランク順'))
        self.all_rank_order=QComboBox()
        self.all_rank_order.addItem('昇順（★1 → ★5）','asc')
        self.all_rank_order.addItem('降順（★5 → ★1）','desc')
        self.all_rank_order.currentIndexChanged.connect(self.refresh_all)
        bar.addWidget(self.all_rank_order); bar.addStretch()
        l.addLayout(bar)
        self.all_table=self.table(['実績名','★ ランク','解除条件','必要回数','イベントID'])
        self.all_table.horizontalHeader().sectionClicked.connect(
            lambda column: self._toggle_rank_order(self.all_rank_order) if column==1 else None)
        l.addWidget(self.all_table); self.tabs.addTab(w,'実績一覧')

    def make_profiles(self):
        w,l=self.page()
        l.addWidget(QLabel('個人実績カード（管理者のみ・OBSには表示しません）'))
        bar=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText('ユーザー名 / ID で検索')
        self.search.textChanged.connect(self.refresh_profiles)
        self.user_select=QComboBox(); self.user_select.currentIndexChanged.connect(self.refresh_card)
        bar.addWidget(self.search); bar.addWidget(self.user_select); l.addLayout(bar)
        self.card_name=QLabel('視聴者を選択してください'); self.card_name.setStyleSheet('font-size:19pt;font-weight:bold;')
        l.addWidget(self.card_name)
        self.card_progress=QProgressBar(); l.addWidget(self.card_progress)
        rank_bar=QHBoxLayout()
        rank_bar.addWidget(QLabel('★ ランク順'))
        self.card_rank_order=QComboBox()
        self.card_rank_order.addItem('昇順（★1 → ★5）','asc')
        self.card_rank_order.addItem('降順（★5 → ★1）','desc')
        self.card_rank_order.currentIndexChanged.connect(self.refresh_card)
        rank_bar.addWidget(self.card_rank_order)
        rank_bar.addStretch()
        l.addLayout(rank_bar)
        self.card_table=self.table(['実績','ランク','状態','進捗','解除日時'])
        self.card_table.horizontalHeader().sectionClicked.connect(
            lambda column: self._toggle_rank_order(self.card_rank_order) if column==1 else None)
        l.addWidget(self.card_table)
        self.tabs.addTab(w,'個人実績カード')

    @staticmethod
    def _toggle_rank_order(combo):
        combo.setCurrentIndex(1 - combo.currentIndex())

    def make_settings(self):
        w,l=self.page()
        group=QGroupBox('接続状況'); f=QFormLayout(group)
        self.twitch_status=QLabel('未接続'); f.addRow('Twitch',self.twitch_status)
        self.bridge_status=QLabel('未接続（手動接続）')
        f.addRow('演出アプリ',self.bridge_status)
        bridge_controls=QHBoxLayout()
        self.bridge_connect_button=QPushButton('TKG接続')
        self.bridge_connect_button.clicked.connect(self.start_bridge_server)
        self.bridge_disconnect_button=QPushButton('TKG切断')
        self.bridge_disconnect_button.clicked.connect(self.stop_bridge_server)
        self.bridge_disconnect_button.setEnabled(False)
        bridge_controls.addWidget(self.bridge_connect_button)
        bridge_controls.addWidget(self.bridge_disconnect_button)
        f.addRow(bridge_controls)
        bridge_help=QLabel('TKG連携の受付中だけ専用実績を一覧とカードに表示します。解除履歴は保持されます。\n任意連携：TKGは同梱しません。接続時のみローカル127.0.0.1:8767で待機します。\n'
                           '連携側は既存の /api/event と認証キーに対応する必要があります。')
        bridge_help.setWordWrap(True)
        f.addRow(bridge_help)
        f.addRow('OBS通知', QLabel('http://127.0.0.1:8766/'))
        self.twitch_channel=QLineEdit(); self.twitch_channel.setPlaceholderText('配信チャンネル名（英数字）')
        self.twitch_channel.setText(str(self.prefs.value('twitch_channel','')))
        self.twitch_nick=QLineEdit()
        self.twitch_nick.setReadOnly(True)
        self.twitch_nick.setText(str(self.prefs.value('twitch_nick','')))
        f.addRow('配信チャンネル',self.twitch_channel)
        f.addRow('認証アカウント',self.twitch_nick)
        self.oauth_button=QPushButton('Twitchでログイン（自動取得）')
        self.oauth_button.clicked.connect(self.oauth_login)
        f.addRow(self.oauth_button)
        self.oauth_logout_button=QPushButton('Twitch認証情報を削除')
        self.oauth_logout_button.clicked.connect(self.oauth_logout)
        f.addRow(self.oauth_logout_button)
        stop=QPushButton('チャット切断')
        stop.clicked.connect(self.disconnect_twitch)
        f.addRow(stop)
        f.addRow(QLabel('※ ブラウザで初回認証。アクセストークンの手入力は不要です。'))
        f.addRow(QLabel('※ TKG連携時はこのアプリでTwitchチャットにも接続してください。'))
        l.addWidget(group)
        emote_group=QGroupBox('特定スタンプ実績の設定'); ef=QFormLayout(emote_group)
        ef.addRow(QLabel('「グットゲーム！！」の対象となるTwitchスタンプ名を指定します。'))
        self.gg_emote_name=QLineEdit()
        self.gg_emote_name.setText(str(self.prefs.value('gg_emote_name','shirat43Gg')))
        self.gg_emote_name.setPlaceholderText('例：shirat43Gg')
        self.gg_emote_name.setMaxLength(100)
        ef.addRow('対象スタンプ名',self.gg_emote_name)
        save_emote=QPushButton('対象スタンプ名を保存')
        save_emote.clicked.connect(self.save_gg_emote)
        ef.addRow(save_emote)
        hint=QLabel('Twitchのエモートタグで実際のスタンプ送信と確認できた場合のみ判定します。\n'
                    'スタンプ名を文字で送っただけでは解除されません。\n'
                    '累計30・50・100個の実績はすべてのTwitchスタンプが対象です。')
        hint.setWordWrap(True)
        ef.addRow(hint)
        l.addWidget(emote_group)
        group2=QGroupBox('通知設定'); f2=QFormLayout(group2)
        self.desktop_check=QCheckBox('配信者画面に表示'); self.desktop_check.setChecked(self.pref_bool('desktop',True)); self.desktop_check.toggled.connect(lambda v:self.prefs.setValue('desktop',v))
        self.obs_check=QCheckBox('OBSに表示'); self.obs_check.setChecked(self.pref_bool('obs',True)); self.obs_check.toggled.connect(lambda v:self.prefs.setValue('obs',v))
        f2.addRow(self.desktop_check); f2.addRow(self.obs_check)
        self.notify_duration=QSpinBox();self.notify_duration.setRange(2,15)
        self.notify_duration.setValue(int(self.prefs.value('duration',5)))
        self.notify_duration.valueChanged.connect(lambda v:self.prefs.setValue('duration',v))
        f2.addRow('表示時間（秒）',self.notify_duration)
        self.obs_url=QLabel('http://127.0.0.1:8766/')
        f2.addRow('OBSブラウザソースURL',self.obs_url)
        l.addWidget(group2)
        sounds=QGroupBox('サウンド設定'); sf=QFormLayout(sounds)
        self.sound_enabled=QCheckBox('実績解除音を再生')
        self.sound_enabled.setChecked(self.pref_bool('sound_enabled',True))
        self.sound_enabled.toggled.connect(lambda v:self.prefs.setValue('sound_enabled',v))
        sf.addRow(self.sound_enabled)
        self.volume=QSlider(Qt.Horizontal);self.volume.setRange(0,100)
        self.volume.setValue(int(self.prefs.value('volume',70)))
        self.volume.valueChanged.connect(lambda v:self.prefs.setValue('volume',v))
        sf.addRow('音量',self.volume)
        self.sound_mode=QComboBox();self.sound_mode.addItem('共通','common');self.sound_mode.addItem('★ランク別','rank')
        self.sound_mode.setCurrentIndex(max(0,self.sound_mode.findData(self.prefs.value('sound_mode','common'))))
        self.sound_mode.currentIndexChanged.connect(lambda _:self.prefs.setValue('sound_mode',self.sound_mode.currentData()))
        sf.addRow('割り当て',self.sound_mode)
        self.sound_labels={}
        for r in range(0,6):
            label=QLabel(self.sound_description(r));label.setWordWrap(True)
            self.sound_labels[r]=label
            row=QHBoxLayout()
            choose=QPushButton('変更');choose.clicked.connect(lambda _, rank=r:self.choose_sound(rank))
            reset=QPushButton('標準');reset.clicked.connect(lambda _, rank=r:self.reset_sound(rank))
            row.addWidget(label,1);row.addWidget(choose);row.addWidget(reset)
            sf.addRow('共通' if r==0 else '★'*r,row)
        preview=QPushButton('サウンド試聴');preview.clicked.connect(lambda:self.play_sound(1,force=True))
        sf.addRow(preview)
        l.addWidget(sounds)
        updates=QGroupBox('アプリのアップデート'); uf=QFormLayout(updates)
        uf.addRow('現在のバージョン', QLabel('v' + update_service.CURRENT_VERSION))
        self.update_status=QLabel('起動後に更新を確認します')
        self.update_status.setWordWrap(True)
        uf.addRow('更新状況', self.update_status)
        self.update_button=QPushButton('今すぐ更新を確認')
        self.update_button.clicked.connect(lambda: self.check_for_updates(True))
        uf.addRow(self.update_button)
        uf.addRow(QLabel('GitHub Releasesを確認します。更新は確認後のみ実行します。'))
        l.addWidget(updates)
        group3=QGroupBox('データ管理'); f3=QFormLayout(group3)
        path_label=QLabel(str(DB_PATH)); path_label.setWordWrap(True)
        backup=QPushButton('データベースをバックアップ'); backup.clicked.connect(self.backup)
        f3.addRow('保存先',path_label); f3.addRow(backup); l.addWidget(group3)
        group4=QGroupBox('メンテナンス'); f4=QVBoxLayout(group4)
        restart=QPushButton('バグ修正'); restart.clicked.connect(self.restart)
        f4.addWidget(QLabel('実際の処理はアプリの再起動です。'))
        f4.addWidget(restart); l.addWidget(group4)
        theme_group=QGroupBox('外観・カラー設定')
        theme_form=QFormLayout(theme_group)
        self.theme_select=QComboBox()
        self.theme_select.addItem('ダーク（暗い背景・白文字）', 'dark')
        self.theme_select.addItem('ライト（明るい背景・黒文字）', 'light')
        self.theme_select.setCurrentIndex(max(0,self.theme_select.findData(self.prefs.value('theme','dark'))))
        self.accent_select=QComboBox()
        for label, value in [('ブルー','blue'),('パープル','purple'),('グリーン','green')]:
            self.accent_select.addItem(label,value)
        self.accent_select.setCurrentIndex(max(0,self.accent_select.findData(self.prefs.value('accent','blue'))))
        self.theme_select.currentIndexChanged.connect(self.change_theme)
        self.accent_select.currentIndexChanged.connect(self.change_theme)
        theme_form.addRow('背景テーマ',self.theme_select)
        theme_form.addRow('アクセントカラー',self.accent_select)
        theme_form.addRow(QLabel('変更内容は自動保存され、次回起動時にも引き継がれます。'))
        l.addWidget(theme_group)
        l.addStretch()
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(w)
        self.tabs.addTab(scroll,'設定・接続')

    def save_gg_emote(self):
        name=self.gg_emote_name.text().strip()
        if not name or not re.fullmatch(r'[A-Za-z0-9_]{1,100}',name):
            QMessageBox.warning(self,'入力エラー','スタンプ名は英数字とアンダースコアで入力してください。')
            return
        self.prefs.setValue('gg_emote_name',name)
        self.prefs.sync()
        self.twitch_worker.target_emote_name=name
        QMessageBox.information(self,'保存完了',f'対象スタンプを「{name}」に変更しました。')

    def change_theme(self):
        self.prefs.setValue('theme', self.theme_select.currentData())
        self.prefs.setValue('accent', self.accent_select.currentData())
        self.apply_theme()

    def apply_theme(self):
        dark = self.prefs.value('theme', 'dark') != 'light'
        accent = self.prefs.value('accent', 'blue')
        palette = {
            'blue': ('#2563EB', '#1D4ED8', '#FFFFFF'),
            'purple': ('#7C3AED', '#6D28D9', '#FFFFFF'),
            'green': ('#047857', '#065F46', '#FFFFFF'),
        }
        primary, hover, button_text = palette.get(accent, palette['blue'])
        if dark:
            bg, panel, field, text, muted, border, header, selected = (
                '#111827','#182335','#202D41','#F3F4F6','#CBD5E1','#40516A','#26374F','#284C82')
        else:
            bg, panel, field, text, muted, border, header, selected = (
                '#F3F6FA','#FFFFFF','#FFFFFF','#182230','#344054','#CBD5E1','#E5EAF2','#C7DAF7')
        self.setStyleSheet(f"""
            QWidget {{ font-family: 'Yu Gothic UI', 'Meiryo'; font-size: 11pt; color: {text}; background-color: {bg}; }}
            QMainWindow, QTabWidget, QTabWidget::pane {{ background-color: {bg}; }}
            QLabel {{ color: {text}; background: transparent; }}
            QTabBar::tab {{ background: {panel}; color: {text}; padding: 12px 18px; border: 1px solid {border}; }}
            QTabBar::tab:selected {{ background: {primary}; color: {button_text}; }}
            QGroupBox {{ color: {text}; background: {panel}; border: 1px solid {border}; border-radius: 8px; margin-top: 14px; padding: 14px; font-weight: bold; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; background: {panel}; color: {text}; }}
            QPushButton {{ background: {primary}; color: {button_text}; padding: 9px 14px; border-radius: 6px; }}
            QPushButton:hover {{ background: {hover}; }}
            QLineEdit, QComboBox, QSpinBox {{ background: {field}; color: {text}; border: 1px solid {border}; border-radius: 5px; padding: 7px; selection-background-color: {selected}; }}
            QComboBox QAbstractItemView {{ background: {field}; color: {text}; selection-background-color: {selected}; }}
            QTableWidget {{ background: {panel}; alternate-background-color: {field}; color: {text}; gridline-color: {border}; selection-background-color: {selected}; selection-color: {text}; }}
            QTableWidget::item {{ color: {text}; }}
            QHeaderView::section {{ background: {header}; color: {text}; padding: 7px; border: 0; }}
            QCheckBox {{ color: {text}; background: transparent; }}
            QProgressBar {{ border: 1px solid {border}; border-radius: 5px; background: {field}; color: {text}; text-align: center; }}
            QProgressBar::chunk {{ background: {primary}; }}
            QMessageBox {{ background: {panel}; color: {text}; }}
            QMessageBox QLabel {{ color: {text}; }}
        """)

    def pref_bool(self,key,default):
        v=self.prefs.value(key,default)
        return v is True or str(v).lower() in ('true','1')

    def sound_description(self,rank):
        path=self.prefs.value('sound_'+str(rank),'')
        return Path(path).name if path else '標準サウンド'

    def choose_sound(self,rank):
        path,_=QFileDialog.getOpenFileName(self,'サウンドを選択','','音声 (*.wav *.mp3)')
        if not path:return
        # 元ファイルの移動・削除による欠落を防ぐ
        dest=BASE/f'custom_sound_{rank}{Path(path).suffix.lower()}'
        try:
            if Path(path).resolve()!=dest.resolve():shutil.copy2(path,dest)
            self.prefs.setValue('sound_'+str(rank),str(dest))
            self.sound_labels[rank].setText(dest.name)
        except Exception as exc:QMessageBox.warning(self,'音声設定エラー',str(exc))

    def reset_sound(self,rank):
        self.prefs.remove('sound_'+str(rank))
        self.sound_labels[rank].setText('標準サウンド')

    def play_sound(self,rank,force=False):
        if not force and not self.sound_enabled.isChecked():return
        key=rank if self.sound_mode.currentData()=='rank' else 0
        path=self.prefs.value('sound_'+str(key),'')
        sound=Path(path) if path else self.default_sound
        if not sound.exists():sound=self.default_sound
        self.player.stop()
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(sound))))
        self.player.setVolume(self.volume.value())
        self.player.play()

    def start_obs_server(self):
        try:
            self.http_server=ThreadingHTTPServer(('127.0.0.1',8766),NotificationHandler)
            threading.Thread(target=self.http_server.serve_forever,daemon=True).start()
            self.obs_url.setText('http://127.0.0.1:8766/ （待機中）')
        except OSError as exc:
            self.obs_url.setText('OBS通知サーバー起動失敗: '+str(exc))

    def start_bridge_server(self):
        global BRIDGE_SIGNAL, BRIDGE_ENABLED
        if self.bridge_server is not None:
            return
        try:
            server=ThreadingHTTPServer(('127.0.0.1',8767),BridgeHandler)
            BRIDGE_SIGNAL=self.bridge_emitter
            BRIDGE_ENABLED=True
            self.bridge_server=server
            threading.Thread(target=server.serve_forever,daemon=True).start()
            self.bridge_status.setText('TKG接続：待機中（127.0.0.1:8767）')
            self.bridge_connect_button.setEnabled(False)
            self.bridge_disconnect_button.setEnabled(True)
            self.v08_editor.refresh()
            self.refresh_all()
        except OSError as exc:
            BRIDGE_ENABLED=False
            BRIDGE_SIGNAL=None
            self.bridge_status.setText('接続失敗：'+str(exc))

    def stop_bridge_server(self):
        global BRIDGE_SIGNAL, BRIDGE_ENABLED
        BRIDGE_ENABLED=False
        BRIDGE_SIGNAL=None
        server=self.bridge_server
        self.bridge_server=None
        if server:
            server.shutdown()
            server.server_close()
        with BRIDGE_EVENT_LOCK:
            BRIDGE_EVENT_IDS.clear()
        self.bridge_status.setText('未接続（手動接続）')
        self.bridge_connect_button.setEnabled(True)
        self.bridge_disconnect_button.setEnabled(False)
        self.v08_editor.refresh()
        self.refresh_all()

    def on_bridge_event(self,user_id,name,event_type):
        try:
            if isinstance(event_type,tuple) and event_type[0]=='chat.keyword_message':
                unlocked=record_event(user_id,name,'chat.keyword_message',keyword_message=event_type[1])
            else:
                unlocked=record_event(user_id,name,event_type[0],event_type[1]) if isinstance(event_type,tuple) else record_event(user_id,name,event_type)
            if unlocked: self.queue_unlocks(unlocked,name)
            self.refresh_all()
            self.bridge_status.setText('イベント受信：'+str(event_type)+' / '+name)
        except Exception as exc:
            self.bridge_status.setText('記録エラー：'+str(exc))

    def queue_unlocks(self,titles,name):
        with connect() as db:
            for title in titles:
                row=db.execute('SELECT rank FROM achievements WHERE title=?',(title,)).fetchone()
                rank=row[0] if row else next((d['rank'] for d in v08_definitions() if d['title']==title),1)
                self.toast_queue.append((title,name,rank))
        self.next_toast()

    def next_toast(self):
        if self.toast_busy or not self.toast_queue:return
        title,name,rank=self.toast_queue.pop(0)
        duration=self.notify_duration.value()
        self.toast_busy=True
        self.notification_serial+=1
        if self.obs_check.isChecked() and self.http_server:
            with NOTIFICATION_LOCK:
                NOTIFICATIONS.append(dict(id=self.notification_serial,title=title,name=name,rank=rank,duration=duration))
                if len(NOTIFICATIONS)>40:del NOTIFICATIONS[:-40]
        if self.desktop_check.isChecked():
            toast=Toast(title,name,rank,duration)
            self.toasts.append(toast)
            toast.show()
            QTimer.singleShot(duration*1000,lambda:self.toasts.remove(toast) if toast in self.toasts else None)
        self.play_sound(rank)
        QTimer.singleShot(duration*1000+250,self.finish_toast)

    def finish_toast(self):
        self.toast_busy=False
        self.next_toast()

    def closeEvent(self,event):
        if self.v08_editor.has_unsaved_changes() and not self.v08_editor.confirm_discard():
            event.ignore(); return
        self.twitch_worker.stop()
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
        self.stop_bridge_server()
        super().closeEvent(event)

    def oauth_login(self):
        client_id = public_client_id()
        if not client_id:
            QMessageBox.warning(self, '設定エラー', 'Twitch Client IDが設定されていません。')
            return
        if self.oauth_busy:
            return
        self.oauth_busy = True
        self.oauth_button.setEnabled(False)
        self.twitch_status.setText('Twitch認証中…')

        def worker():
            try:
                token = twitch_oauth.restore(client_id)
                if not token:
                    token = twitch_oauth.login(client_id)
                identity = twitch_oauth.get_identity(token)
                if identity.get('client_id') != client_id or 'chat:read' not in identity.get('scopes', []):
                    raise RuntimeError('Client IDまたはチャット読み取り権限が一致しません。')
                self.oauth_events.success.emit(identity['login'], token, client_id)
            except Exception as exc:
                self.oauth_events.failure.emit(str(exc))
        threading.Thread(target=worker, daemon=True).start()

    def on_oauth_success(self, nick, token, client_id):
        self.oauth_busy = False
        self.oauth_button.setEnabled(True)
        self.twitch_nick.setText(nick)
        channel = self.twitch_channel.text().strip().lstrip('#').lower() or nick
        if not re.fullmatch(r'[a-z0-9_]{3,25}', channel):
            self.on_oauth_failure('配信チャンネル名を確認してください。')
            return
        self.twitch_channel.setText(channel)
        self.prefs.setValue('twitch_channel', channel)
        self.prefs.setValue('twitch_nick', nick)
        global BRIDGE_TOKEN, BRIDGE_CLIENT_ID
        with BRIDGE_TOKEN_LOCK:
            BRIDGE_TOKEN, BRIDGE_CLIENT_ID = token, client_id
        self.twitch_worker.start(channel, nick, token)

    def on_oauth_failure(self, message):
        self.oauth_busy = False
        self.oauth_button.setEnabled(True)
        self.twitch_status.setText('Twitch認証に失敗しました')
        QMessageBox.warning(self, 'Twitch認証エラー', message)

    def oauth_logout(self):
        client_id = public_client_id()
        if client_id:
            try:
                twitch_oauth.clear(client_id)
            except Exception as exc:
                QMessageBox.warning(self, '認証情報の削除エラー', str(exc))
                return
        self.disconnect_twitch()
        self.twitch_nick.clear()
        QMessageBox.information(self, 'ログアウト', '保存されたTwitch認証情報を削除しました。')

    def disconnect_twitch(self):
        global BRIDGE_TOKEN, BRIDGE_CLIENT_ID
        with BRIDGE_TOKEN_LOCK:
            BRIDGE_TOKEN=None; BRIDGE_CLIENT_ID=None
        self.twitch_worker.stop()
        self.twitch_status.setText('未接続')

    def _on_tab_changed(self,index):
        if self._tab_guard:return
        if index!=self._last_tab_index and self.tabs.widget(self._last_tab_index) is self.v08_editor:
            if not self.v08_editor.confirm_discard():
                self._tab_guard=True
                self.tabs.setCurrentIndex(self._last_tab_index)
                self._tab_guard=False
                return
            # Leaving the editor discards the unsaved draft.
            if self.v08_editor.has_unsaved_changes(): self.v08_editor._reset_form()
        self._last_tab_index=index
        self.refresh_all()

    def on_twitch_event(self,user_id,name,event_type):
        try:
            if isinstance(event_type,tuple) and event_type[0]=='chat.keyword_message':
                unlocked=record_event(user_id,name,'chat.keyword_message',keyword_message=event_type[1])
            else:
                unlocked=record_event(user_id,name,event_type[0],event_type[1]) if isinstance(event_type,tuple) else record_event(user_id,name,event_type)
            if unlocked: self.queue_unlocks(unlocked,name)
            self.refresh_all()
        except Exception as exc:
            self.twitch_status.setText('記録エラー：'+str(exc))

    def clear_dashboard_log(self):
        # Clearing only changes the session's lower bound, not the database.
        with connect() as db:
            self.dashboard_after_id=db.execute('SELECT COALESCE(MAX(id),0) FROM event_log').fetchone()[0]
        self.recent.setRowCount(0)

    @staticmethod
    def is_new_unlock(value):
        if not value or value == '-':
            return False
        try:
            unlocked_at=datetime.fromisoformat(value)
            now=datetime.now(unlocked_at.tzinfo) if unlocked_at.tzinfo else datetime.now()
            age=now-unlocked_at
            return timedelta(0) <= age < timedelta(hours=12)
        except (TypeError,ValueError,OverflowError):
            return False

    def refresh_all(self):
        with connect() as db:
            users=db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            visible_ids=[a[0] for a in visible_legacy_achievements()]
            placeholders=','.join('?' for _ in visible_ids)
            unlocks=db.execute(f'SELECT COUNT(*) FROM progress WHERE unlocked_at IS NOT NULL AND achievement_id IN ({placeholders})', visible_ids).fetchone()[0]
            visible_custom=[d['id'] for d in visible_v08_definitions()]
            if visible_custom:
                placeholders=','.join('?' for _ in visible_custom)
                unlocks+=db.execute(f'SELECT COUNT(*) FROM v08_progress WHERE achievement_id IN ({placeholders})',visible_custom).fetchone()[0]
            self.stats.setText(f'登録視聴者  {users} 人      累計実績解除  {unlocks} 件')
            rows=db.execute('''SELECT e.occurred_at,u.display_name,
                    COALESCE(a.title,d.title,'（削除済み実績）')
                FROM event_log e
                JOIN users u ON e.user_id=u.user_id
                LEFT JOIN achievements a ON e.achievement_id=a.achievement_id
                LEFT JOIN v08_achievement_definitions d ON e.achievement_id=d.id
                WHERE e.id > ?
                ORDER BY e.id DESC LIMIT 50''',(self.dashboard_after_id,)).fetchall()
            self.fill(self.recent,rows)
            visible_ids={a[0] for a in visible_legacy_achievements()}
            legacy_rows=db.execute("SELECT achievement_id,title,rank,description,target,event_type FROM achievements WHERE achievement_id LIKE 'v06_%' ORDER BY rank,achievement_id").fetchall()
            displayed=[(title,'★'*rank+'☆'*(5-rank),description,target,event_type)
                       for aid,title,rank,description,target,event_type in legacy_rows if aid in visible_ids]
            for d in visible_v08_definitions():
                if not d['enabled']:continue
                conditions=d['conditions']
                summary=('  '+d['operator']+'  ').join(c['event_type']+((' : '+c['keyword']) if 'keyword' in c else '') for c in conditions)
                displayed.append((d['title'],'★'*d['rank']+'☆'*(5-d['rank']),summary,
                    ' / '.join(str(c['target']) for c in conditions), 'カスタム'))
            displayed=sort_achievements(displayed, self.all_rank_order.currentData(), rank_index=1)
            self.fill(self.all_table,displayed)
        self.refresh_profiles()

    def refresh_profiles(self):
        previous=self.user_select.currentData()
        term='%'+self.search.text().strip()+'%'
        with connect() as db:
            users=db.execute('SELECT user_id,display_name FROM users WHERE user_id LIKE ? OR display_name LIKE ? ORDER BY display_name',(term,term)).fetchall()
        self.user_select.blockSignals(True); self.user_select.clear()
        for uid,name in users:
            self.user_select.addItem(f'{name} ({uid})',uid)
        idx=self.user_select.findData(previous)
        if idx>=0: self.user_select.setCurrentIndex(idx)
        self.user_select.blockSignals(False)
        self.refresh_card()

    def refresh_card(self):
        uid=self.user_select.currentData()
        if not uid:
            self.card_name.setText('視聴者を選択してください'); self.card_progress.setValue(0)
            self.card_table.setRowCount(0); return
        with connect() as db:
            name=db.execute('SELECT display_name FROM users WHERE user_id=?',(uid,)).fetchone()[0]
            legacy=db.execute('''SELECT a.achievement_id,a.title,a.rank,COALESCE(p.count,0),a.target,p.unlocked_at
                FROM achievements a LEFT JOIN progress p ON p.achievement_id=a.achievement_id AND p.user_id=?
                WHERE a.achievement_id LIKE 'v06_%'
                ORDER BY a.rank,a.title''',(uid,)).fetchall()
            visible_ids={a[0] for a in visible_legacy_achievements()}
            rows=[(title,rank,count,target,at) for aid,title,rank,count,target,at in legacy
                  if aid in visible_ids]
            custom=[]
            for d in visible_v08_definitions(True):
                achieved,percent,counts,targets=v08_status(db,uid,d)
                at=db.execute('SELECT unlocked_at FROM v08_progress WHERE user_id=? AND achievement_id=?',(uid,d['id'])).fetchone()
                custom.append((d['title'],d['rank'],bool(at),f'{percent}% ({" / ".join(str(min(n,t))+"/"+str(t) for n,t in zip(counts,targets))})',at[0] if at else None))
        done=sum(bool(x[4]) for x in rows)+sum(x[2] for x in custom); total=len(rows)+len(custom)
        self.card_name.setText(f'🏆 {name}   —   {done} / {total} 解除')
        self.card_progress.setValue(round(done*100/total) if total else 0)
        card_rows=[(title,'★'*rank+'☆'*(5-rank),'解除済み' if at else '未解除',f'{min(count,target)} / {target}',at or '-') for title,rank,count,target,at in rows]
        card_rows.extend((title,'★'*rank+'☆'*(5-rank),'解除済み' if done else '未解除',progress,at or '-') for title,rank,done,progress,at in custom)
        card_rows=sort_achievements(card_rows, self.card_rank_order.currentData(), rank_index=1)
        self.fill(self.card_table,card_rows)
        # Display NEW without altering the persisted unlock status.
        for index,row in enumerate(card_rows):
            if row[2] == '解除済み' and self.is_new_unlock(row[4]):
                title_item=self.card_table.item(index,0)
                if title_item:
                    title_item.setText('NEW  ' + title_item.text())
                    title_item.setToolTip('解除から12時間以内の新しい実績')
        self.highlight_unlocked_card_rows(card_rows)

    def highlight_unlocked_card_rows(self, card_rows):
        # Highlight by the unlocked state, not the row index: sorting is safe.
        # This changes presentation only; progress and SQLite data are untouched.
        unlocked_background = QColor('#183F48')
        unlocked_text = QColor('#E4FFF5')
        unlocked_status = QColor('#6CE0AE')
        for row_index, row in enumerate(card_rows):
            is_unlocked = row[2] == '解除済み'
            for column_index in range(self.card_table.columnCount()):
                item = self.card_table.item(row_index, column_index)
                if item is None:
                    continue
                if is_unlocked:
                    item.setBackground(unlocked_background)
                    if column_index != 1:  # Keep the existing star-rank color.
                        item.setForeground(unlocked_status if column_index == 2 else unlocked_text)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setToolTip('解除済みの実績')
                else:
                    item.setToolTip('未解除の実績')

    def check_for_updates(self, manual=False):
        if self.update_busy or self.update_download_busy:
            return
        self.update_busy = True
        self.update_button.setEnabled(False)
        self.update_status.setText('GitHub Releasesを確認中…')
        def worker():
            try:
                result = update_service.find_update()
                self.update_events.checked.emit(result, manual)
            except Exception as exc:
                self.update_events.failed.emit(str(exc), manual)
        threading.Thread(target=worker, daemon=True).start()

    def on_update_checked(self, info, manual):
        self.update_busy = False
        self.update_button.setEnabled(True)
        if not info:
            self.update_status.setText('現在のバージョンが最新です')
            if manual:
                QMessageBox.information(self, '更新確認', '新しいバージョンはありません。')
            return
        self.update_info = info
        self.update_status.setText('新しいバージョン: v' + info['version'])
        answer = QMessageBox.question(
            self, 'アップデートがあります',
            '現在: v' + update_service.CURRENT_VERSION + '\n'
            '新しいバージョン: v' + info['version'] + '\n\n'
            'GitHub Releasesからインストーラーをダウンロードしますか？\n'
            '（ダウンロード後、インストール前にも確認します）',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.start_update_download(info)

    def on_update_check_failed(self, message, manual):
        self.update_busy = False
        self.update_button.setEnabled(True)
        self.update_status.setText('更新確認に失敗しました（オフラインでも使用できます）')
        if manual:
            QMessageBox.warning(self, '更新確認エラー', message)

    def start_update_download(self, info):
        if self.update_download_busy:
            return
        self.update_download_busy = True
        self.update_button.setEnabled(False)
        self.update_status.setText('インストーラーをダウンロード中…')
        def worker():
            try:
                path = update_service.download_installer(
                    info, lambda current, total: self.update_events.progress.emit(int(current * 100 / total)))
                self.update_events.downloaded.emit(path)
            except Exception as exc:
                self.update_events.download_failed.emit(str(exc))
        threading.Thread(target=worker, daemon=True).start()

    def on_update_progress(self, percent):
        self.update_status.setText(f'ダウンロード中… {percent}%')

    def on_update_download_failed(self, message):
        self.update_download_busy = False
        self.update_button.setEnabled(True)
        self.update_status.setText('ダウンロードに失敗しました')
        QMessageBox.warning(self, '更新エラー', message)

    def on_update_downloaded(self, path):
        self.update_download_busy = False
        self.update_button.setEnabled(True)
        self.update_status.setText('インストーラーをダウンロードしました')
        if self.v08_editor.has_unsaved_changes():
            QMessageBox.information(self, '未保存の編集', '実績管理に未保存の変更があります。保存または破棄してから更新してください。')
            return
        answer = QMessageBox.question(
            self, 'アップデートのインストール',
            '既存の実績データをバックアップしてからアプリを終了し、\n'
            '新しいインストーラーを起動します。よろしいですか？\n\n'
            'Windowsのインストール画面でも操作が必要です。',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            backup_path = BASE / ('achievements_pre_update_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.db')
            with connect() as source, sqlite3.connect(str(backup_path)) as target:
                source.backup(target)
            if not QProcess.startDetached(path, []):
                raise RuntimeError('インストーラーを起動できませんでした。')
        except Exception as exc:
            QMessageBox.critical(self, '更新準備エラー', str(exc))
            return
        QApplication.instance().quit()

    def backup(self):
        dst=BASE / ('achievements_backup_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.db')
        try:
            with connect() as source, sqlite3.connect(str(dst)) as target:
                source.backup(target)
            QMessageBox.information(self,'バックアップ完了',f'保存しました:\n{dst}')
        except Exception as exc:
            QMessageBox.critical(self,'バックアップ失敗',str(exc))

    def restart(self):
        if QMessageBox.question(self,'バグ修正','実績管理アプリを再起動しますか？',QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:
            return
        # 先に通知サーバーを閉じ、再起動後のポート競合を防ぐ。
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
            self.http_server=None
        self.stop_bridge_server()
        import subprocess
        try:
            if getattr(sys,'frozen',False):
                cmd=[sys.executable]
            else:
                cmd=[sys.executable,str(Path(__file__).resolve())]
            subprocess.Popen(cmd,cwd=str(Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent))
        except Exception as exc:
            QMessageBox.critical(self,'再起動失敗',str(exc)); self.start_obs_server(); return
        QApplication.instance().quit()

if __name__=='__main__':
    init_db()
    app=QApplication(sys.argv)
    window=App(); window.show()
    sys.exit(app.exec_())
