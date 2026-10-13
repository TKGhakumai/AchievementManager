# Achievement Manager v0.8.0-beta.1 — Windows 配布準備版

このZIPは**Windows EXE / インストーラーを作るためのソース一式**です。完成済みのEXEは含みません。

## v0.8で確認する機能
- 実績作成・編集、保存前の変更破棄確認、特殊条件（Beta）
- 実績一覧・個人実績カードへの反映と★昇順・降順
- 個人実績カードの解除済み実績を青緑色・太字で強調（Stage 8修正を含む）
- コメント等の実績判定・解除履歴・OBS通知
- 手動TKG連携受付（TKG本体側の送信実装は別途必要）

## GitHub Actionsでインストーラー作成（推奨）
1. **develop-v0.8**ブランチにこのZIPの中身をアップロード。`.github/workflows/windows-build.yml`を含め、リポジトリのルートに配置。
2. GitHub → Actions → **Windows v0.8 Beta installer** → **Run workflow** でdevelop-v0.8を選択。
3. 成功後、実行履歴のArtifactsから `AchievementManager-Setup-v0.8.0-beta.1` をダウンロード。ZIP内にWindowsインストーラーのEXEが入ります。
4. Windows実機でインストール、起動、v0.7からの更新、DB保持、解除済み強調表示、Twitch/OBS接続、アンインストールを検証。
5. 検証完了後にGitHub Releases → Draft a new release → tag `v0.8.0-beta.1`、Targetは検証済みコミット、**Set as a pre-release**にチェック。Actionsで作成したインストーラーを添付して公開。

**注意:** タグをpushするとActionsが走りますが、Releasesへの自動公開は行いません。

## Windowsローカルビルド
Python 3.12、PowerShell、Inno Setup 6が必要です。
```
./build/build_windows.ps1
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' 'installer\setup.iss'
```
Windows上で `dist/AchievementManager/AchievementManager.exe` と `dist-installer/AchievementManager-Setup-v0.8.0-beta.1.exe` が生成されます。

## 重要な互換性・制限
- v0.7と同じInno Setup AppIdとインストール先を使用し、上書き更新を想定します。
- DBは `%LOCALAPPDATA%\AchievementManager\achievements.db` に保存され、アプリ更新時に削除しません。**必ず手動バックアップ**してから更新してください。
- このv0.8 Stage 8のTwitch接続画面は**手動アクセストークン入力方式**です。v0.7のPKCE自動ログインはこのソースに含まれていません。以前の自動ログインが必須なら**公開前に復元・統合が必要**です。
- TKG本体ソース、個人用素材、トークン、Client Secret、ユーザーDBを公開しないでください。
- v0.8インストーラーはこの環境では実ビルド・起動未検証。Windows GitHub Actionsの結果と実機テストが必要です。
- GitHub Releasesへの自動公開、アプリ内自動更新は含みません。
- `main.py` は標準ライブラリとPyQt5を使用し、`achievement_editor.py` と `achievement_core/` を同梱します。
