"""Upgrade the already-patched local TKG v0.5 Python file to v0.6; preserve credentials."""
from pathlib import Path
import shutil,sys

MARK='# Achievement Manager v0.6 detail bridge'

def upgrade(path):
    path=Path(path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower()!='.py': raise ValueError('TKGの .py ファイルを指定してください')
    s=path.read_text(encoding='utf-8-sig')
    if MARK in s:
        print('v0.6連携は導入済みです'); return
    if '# Achievement Manager v0.5 bridge' not in s:
        raise ValueError('先にv0.5連携済みのTKGソースを指定してください。ファイルは変更していません。')
    checks=[
      '        print(f"🎯 発動: {name} / {user}")',
      '                QtCore.Q_ARG(object, pix)\n            )\n\n        except Exception as e:\n            print("アイコンエラー:", e)',
      '    @QtCore.pyqtSlot(object)\n    def _add_icons(self, pix):',
      '        is_big = random.random() < 0.05',
      '        if random.random() < 0.01:',
    ]
    if any(c not in s for c in checks): raise ValueError('想定するTKG v7構造と異なります。変更していません。')
    s=s.replace('# Achievement Manager v0.5 bridge','# Achievement Manager v0.5 bridge\n'+MARK,1)
    anchor='        print(f"🎯 発動: {name} / {user}")'
    # Existing v0.5 bridge sends effect.used and hacking.used. Add detailed event only.
    insert='''
        # v0.6: five specific channel-point effects; no duplicates in general counter.
        if "スモーク" in name:
            send_tkg_event(user, "effect.smoke")
        elif "通り" in name:
            send_tkg_event(user, "effect.passing")
        elif "フラッシュ" in name:
            send_tkg_event(user, "effect.flash")
        elif "画面割ったる" in name or "ガラス" in name:
            send_tkg_event(user, "effect.glass")
        elif "おじゃましま～す" in name or "お邪魔します" in name:
            send_tkg_event(user, "effect.meteor")
'''
    s=s.replace(anchor,anchor+insert,1)
    # Only change the icon-loading call, not meteor-loading. Preserve username for real lottery outcome.
    old='                QtCore.Q_ARG(object, pix)\n            )\n\n        except Exception as e:\n            print("アイコンエラー:", e)'
    s=s.replace(old,'                QtCore.Q_ARG(object, (pix, username))\n            )\n\n        except Exception as e:\n            print("アイコンエラー:", e)',1)
    s=s.replace('    def _add_icons(self, pix):\n\n        is_big = random.random() < 0.05',
                '    def _add_icons(self, pix):\n\n        pix, achievement_user = pix\n        is_big = random.random() < 0.05\n        if is_big:\n            send_tkg_event(achievement_user, "passing.giant")',1)
    s=s.replace('        if random.random() < 0.01:\n            print("🎆 花火当たり")',
                '        if random.random() < 0.01:\n            send_tkg_event(achievement_user, "passing.fireworks")\n            print("🎆 花火当たり")',1)
    if s.count('send_tkg_event(achievement_user,')!=2: raise ValueError('レア演出の変更に失敗')
    compile(s,str(path),'exec')
    backup=path.with_name(path.stem+'.before_achievement_v06.py')
    if backup.exists(): raise FileExistsError('バックアップが既に存在します: '+str(backup))
    shutil.copy2(path,backup)
    path.write_text(s,encoding='utf-8')
    print('v0.6連携追加完了:',path)
    print('バックアップ:',backup)
    print('元の認証情報や演出の抽選確率は変更していません。')

if __name__=='__main__':
    try:
        target=sys.argv[1] if len(sys.argv)>1 else input('v0.5連携済みTKG .py のフルパス: ').strip().strip('"')
        upgrade(target)
    except Exception as e:
        print('エラー:',e);sys.exit(1)
