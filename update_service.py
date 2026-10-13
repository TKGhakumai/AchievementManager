"""Read-only GitHub Releases checker and verified installer downloader.

No GitHub credentials are needed. Never executes downloaded content by itself.
"""
import hashlib
import json
import re
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

CURRENT_VERSION = '0.8.0-beta.6'
REPO = 'TKGhakumai/AchievementManager'
API_URL = f'https://api.github.com/repos/{REPO}/releases?per_page=30'
MAX_INSTALLER_SIZE = 250 * 1024 * 1024
INSTALLER_PATTERN = re.compile(r'^AchievementManager-Setup-v(\d+\.\d+\.\d+(?:-beta\.\d+)?)\.exe$', re.I)
VERSION_PATTERN = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:-beta\.(\d+))?$')


def version_key(value):
    match = VERSION_PATTERN.fullmatch(value.lstrip('v'))
    if not match:
        return None
    major, minor, patch, beta = match.groups()
    return (int(major), int(minor), int(patch), 0 if beta is not None else 1, int(beta or 0))


def _https_json(url):
    request = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': f'AchievementManager/{CURRENT_VERSION}',
        'X-GitHub-Api-Version': '2022-11-28',
    })
    with urllib.request.urlopen(request, timeout=12) as response:
        if response.status != 200:
            raise RuntimeError(f'GitHub API HTTP {response.status}')
        return json.load(response)


def find_update():
    """Find the highest published newer release, including prereleases."""
    releases = _https_json(API_URL)
    current = version_key(CURRENT_VERSION)
    candidates = []
    for release in releases:
        if release.get('draft') or not release.get('published_at'):
            continue
        version = str(release.get('tag_name', '')).lstrip('v')
        key = version_key(version)
        if key is None or key <= current:
            continue
        for asset in release.get('assets', []):
            name = asset.get('name', '')
            match = INSTALLER_PATTERN.fullmatch(name)
            if not match or match.group(1) != version:
                continue
            url = asset.get('browser_download_url', '')
            parsed = urlparse(url)
            expected_prefix = f'/TKGhakumai/AchievementManager/releases/download/v{version}/'
            if parsed.scheme != 'https' or parsed.hostname != 'github.com' or not parsed.path.startswith(expected_prefix):
                continue
            size = int(asset.get('size') or 0)
            if size <= 0 or size > MAX_INSTALLER_SIZE:
                continue
            candidates.append((key, {
                'version': version,
                'tag': release['tag_name'],
                'notes': (release.get('body') or '')[:2000],
                'name': name,
                'url': url,
                'size': size,
                'digest': asset.get('digest') or '',
                'release_url': release.get('html_url', ''),
            }))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def download_installer(update, progress=None):
    """Download to a temporary directory; validate size, SHA256 when published, and MZ header."""
    url = update['url']
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'github.com' or not INSTALLER_PATTERN.fullmatch(update['name']):
        raise ValueError('ダウンロード先またはファイル名が不正です。')
    directory = Path(tempfile.mkdtemp(prefix='achievement-manager-update-'))
    final_path = directory / update['name']
    part_path = directory / (update['name'] + '.part')
    request = urllib.request.Request(url, headers={'User-Agent': f'AchievementManager/{CURRENT_VERSION}'})
    digest = hashlib.sha256()
    total = 0
    try:
        with urllib.request.urlopen(request, timeout=30) as response, part_path.open('wb') as output:
            for chunk in iter(lambda: response.read(1024 * 256), b''):
                total += len(chunk)
                if total > MAX_INSTALLER_SIZE or total > update['size']:
                    raise ValueError('インストーラーのサイズが不正です。')
                digest.update(chunk)
                output.write(chunk)
                if progress:
                    progress(total, update['size'])
        if total != update['size']:
            raise ValueError('インストーラーのサイズが一致しません。')
        published_digest = update.get('digest', '')
        if published_digest:
            if not published_digest.startswith('sha256:') or digest.hexdigest().lower() != published_digest[7:].lower():
                raise ValueError('SHA256検証に失敗しました。')
        with part_path.open('rb') as f:
            if f.read(2) != b'MZ':
                raise ValueError('ダウンロードファイルはWindows EXEではありません。')
        part_path.rename(final_path)
        return str(final_path)
    except Exception:
        part_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        try:
            directory.rmdir()
        except OSError:
            pass
        raise
