"""TKG side helper: send event to Achievement Manager without blocking effects."""
import json
import os
import secrets
import threading
import urllib.request
from pathlib import Path

KEY_FILE = Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'AchievementManager' / 'bridge_key.txt'
URL = 'http://127.0.0.1:8767/api/event'

def send_tkg_event(login, event_type):
    if not login or not KEY_FILE.exists():
        return
    def worker():
        try:
            payload=json.dumps({'login':login.lower().strip(), 'event_type':event_type,
                                'event_id':secrets.token_hex(16)}).encode('utf-8')
            request=urllib.request.Request(URL, data=payload, method='POST', headers={
                'Content-Type':'application/json',
                'X-Achievement-Key':KEY_FILE.read_text(encoding='utf-8').strip()})
            with urllib.request.urlopen(request,timeout=7) as response:
                response.read()
        except Exception as exc:
            print('[Achievement Manager] イベント送信失敗:', type(exc).__name__, str(exc))
    threading.Thread(target=worker,daemon=True).start()
