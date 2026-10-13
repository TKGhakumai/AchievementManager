"""Patch user's local TKG v7 file in place, with backup. Does not bundle or print credentials."""
import shutil
import sys
from pathlib import Path

MARK = '# Achievement Manager v0.5 bridge'

def patch(path):
    path=Path(path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower()!='.py':
        raise ValueError('Python (.py) ファイルを指定してください。')
    s=path.read_text(encoding='utf-8-sig')
    if MARK in s:
        print('連携処理はすでに追加されています。'); return
    required=['    def handle_trigger(self, name, user, user_input=""):',
              '    def spawn_hacking_user(self, username):',
              '        self.hacking_request_serial += 1']
    if any(x not in s for x in required):
        raise ValueError('対応するTKG v7ソースではありません。ファイルは変更しませんでした。')
    helper=Path(__file__).with_name('tkg_bridge_client.py')
    if not helper.is_file(): raise FileNotFoundError(helper)
    s=s.replace('import sys\n','import sys\n'+MARK+'\nfrom tkg_bridge_client import send_tkg_event\n',1)
    s=s.replace('        print(f"🎯 発動: {name} / {user}")',
                '        print(f"🎯 発動: {name} / {user}")\n'
                '        if any(word in name for word in ("ハッキング", "スモーク", "通り", "フラッシュ", "画面割ったる", "おじゃましま～す", "フォトタイム")):\n'
                '            send_tkg_event(user, "effect.used")\n'
                '            if "ハッキング" in name:\n'
                '                send_tkg_event(user, "hacking.used")',1)
    needle='        self.hacking_request_serial += 1'
    replacement=('        if rare_type == "giant":\n'
                 '            send_tkg_event(username, "hacking.giant")\n'
                 '        elif rare_type == "swarm":\n'
                 '            send_tkg_event(username, "hacking.swarm")\n\n'+needle)
    s=s.replace(needle,replacement,1)
    if s.count('send_tkg_event(')!=4:
        raise ValueError('パッチ検証に失敗しました。変更しませんでした。')
    compile(s,str(path),'exec')
    backup=path.with_suffix('.before_achievement_v05.py')
    if backup.exists():
        raise FileExistsError('バックアップがすでに存在します: '+str(backup))
    shutil.copy2(path,backup)
    shutil.copy2(helper,path.parent/helper.name)
    path.write_text(s,encoding='utf-8')
    print('連携追加完了:',path.name)
    print('元ファイルのバックアップ:',backup.name)
    print('元の認証設定・演出内容は変更していません。')

if __name__=='__main__':
    try:
        if len(sys.argv)>1: target=sys.argv[1]
        else: target=input('TKG v7の .py ファイルのフルパス: ').strip().strip('"')
        patch(target)
    except Exception as exc:
        print('エラー:',exc)
        sys.exit(1)
