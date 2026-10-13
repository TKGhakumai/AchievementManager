"""Run with: python test_emote_matching.py (no Qt needed)."""
import ast
from pathlib import Path
import re
import unicodedata

source = Path(__file__).with_name('main.py').read_text(encoding='utf-8')
node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'parse_chat_events')
namespace = {'re': re, 'unicodedata': unicodedata}
exec(compile(ast.Module(body=[node], type_ignores=[]), 'main.py', 'exec'), namespace)
parse = namespace['parse_chat_events']

assert 'chat.gg' in parse('shirat43Gg', '123:0-9', 'shirat43Gg')
assert 'chat.gg' not in parse('shirat43Gg', '', 'shirat43Gg')
assert 'chat.gg' not in parse('shirat43Gg', '123:0-9', 'otherEmote')
assert 'chat.gg' in parse('otherEmote', '456:0-9', 'otherEmote')
assert ('chat.emote', 2) in parse('shirat43Gg shirat43Gg', '123:0-9,11-20', 'shirat43Gg')
assert 'chat.gg' not in parse('shirat43Gg', '123:0-9', '')
assert 'chat.gg' in parse('😀shirat43Gg', '123:2-11', 'shirat43Gg')
print('Emote matching tests: OK')
