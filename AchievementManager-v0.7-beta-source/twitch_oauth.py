"""Twitch OAuth authorization-code PKCE for a Windows public client.
No client secret is used. Tokens are stored in the OS credential vault via keyring.
"""
import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import keyring

REDIRECT_URI = 'http://localhost:3000/'
SERVICE = 'AchievementManager.TwitchOAuth.v07'
SCOPES = 'chat:read'


def _post_token(values):
    body = urllib.parse.urlencode(values).encode('utf-8')
    req = urllib.request.Request('https://id.twitch.tv/oauth2/token', data=body,
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def _save(client_id, result):
    result['saved_at'] = int(time.time())
    keyring.set_password(SERVICE, client_id, json.dumps(result))


def clear(client_id):
    try:
        keyring.delete_password(SERVICE, client_id)
    except keyring.errors.PasswordDeleteError:
        pass


def restore(client_id):
    raw = keyring.get_password(SERVICE, client_id)
    if not raw:
        return None
    saved = json.loads(raw)
    if saved.get('saved_at', 0) + saved.get('expires_in', 0) > time.time() + 120:
        return saved['access_token']
    if not saved.get('refresh_token'):
        return None
    result = _post_token({'client_id': client_id, 'grant_type': 'refresh_token',
                          'refresh_token': saved['refresh_token']})
    if 'refresh_token' not in result:
        result['refresh_token'] = saved['refresh_token']
    _save(client_id, result)
    return result['access_token']


def login(client_id, timeout=180):
    """Blocking; call from a worker thread. Redirect URI must match developer console."""
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    outcome = {}
    arrived = threading.Event()

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            args = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if args.get('state', [''])[0] != state:
                self.send_error(400, 'Invalid OAuth state')
                return
            if args.get('code'):
                outcome['code'] = args['code'][0]
            else:
                outcome['error'] = args.get('error_description', args.get('error', ['Authorization denied']))[0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write('<html><meta charset="utf-8"><body><h2>認証を受け付けました。アプリに戻ってください。</h2></body></html>'.encode())
            arrived.set()

        def log_message(self, *_):
            pass

    # Bind only loopback; do not expose OAuth callback to the network.
    server = HTTPServer(('127.0.0.1', 3000), Callback)
    server.timeout = 1
    try:
        params = urllib.parse.urlencode({
            'response_type': 'code', 'client_id': client_id, 'redirect_uri': REDIRECT_URI,
            'scope': SCOPES, 'state': state, 'code_challenge': challenge,
            'code_challenge_method': 'S256', 'force_verify': 'true'})
        webbrowser.open('https://id.twitch.tv/oauth2/authorize?' + params)
        deadline = time.monotonic() + timeout
        while not arrived.is_set() and time.monotonic() < deadline:
            server.handle_request()
        if not arrived.is_set():
            raise TimeoutError('Twitch認証が時間切れになりました。')
        if 'error' in outcome:
            raise RuntimeError(outcome['error'])
        result = _post_token({'client_id': client_id, 'grant_type': 'authorization_code',
                              'code': outcome['code'], 'redirect_uri': REDIRECT_URI,
                              'code_verifier': verifier})
        _save(client_id, result)
        return result['access_token']
    finally:
        server.server_close()


def get_identity(token):
    req = urllib.request.Request('https://id.twitch.tv/oauth2/validate',
                                 headers={'Authorization': 'OAuth ' + token})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)
