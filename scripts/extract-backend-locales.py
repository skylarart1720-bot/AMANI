"""Extract public errors and admin setup labels from source, never runtime data."""
import ast
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
base = ROOT / 'apps/orchestrator/src/locales'
source = json.loads((base / 'en.json').read_text(encoding='utf-8'))
tree = ast.parse((ROOT / 'apps/orchestrator/src/support.py').read_text(encoding='utf-8'))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'HTTPException' and len(node.args) > 1:
        error = node.args[1]
        if isinstance(error, ast.Constant) and isinstance(error.value, str): source[error.value] = error.value
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'setup':
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str) and (' ' in child.value or child.value[:1].isupper()) and not child.value.startswith('SELECT '):
                text = child.value.strip()
                source[text] = text
for text in ('Too many requests. Please wait a minute.', 'Moderator authentication required.', 'Super Admin access required.'):
    source[text] = text
source.pop(' active accounts', None)
source.pop(' contacts need checking', None)
(base / 'en.json').write_text(json.dumps(source, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{len(source)} UI, setup and error keys')
