"""Keep Playwright's failure snapshots from printing configured credentials."""
import sys
import traceback
from pathlib import Path
from dotenv import dotenv_values

def install_secret_redaction():
    root = Path(__file__).resolve().parents[1]
    def safe_exception(kind, value, trace):
        output = ''.join(traceback.format_exception(kind, value, trace))
        values = dotenv_values(root / '.env')
        secrets = [item for key, item in values.items() if item and len(item) >= 12 and any(word in key for word in ('TOKEN','SECRET','API_KEY','ENCRYPTION_KEY'))]
        token_file = root / 'data/.admin-token'
        if token_file.exists(): secrets.append(token_file.read_text(encoding='utf-8').strip())
        for secret in secrets:
            if secret: output = output.replace(secret, '[credential redacted]')
        sys.stderr.write(output)
    sys.excepthook = safe_exception
