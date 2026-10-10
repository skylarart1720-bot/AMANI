"""Complete selected public catalogues with the configured provider and export them.

Run after restoring AI credits. No visitor data is read. Existing edits are kept.
After native-speaker review, run seed-locales.py and rebuild both frontends.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
sys.path.insert(0, str(ROOT / 'apps/orchestrator/src'))
import languages

async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('codes', nargs='+', choices=list(languages.REGISTRY))
    args = parser.parse_args()
    data = Path(os.getenv('AMANI_DATA_DIR', str(ROOT / 'data')))
    data.mkdir(parents=True, exist_ok=True)
    for code in args.codes:
        result = await languages.complete(code, data)
        print(f"{code}: {result['translated']}/{result['total']} ({result['status']})")
        if result['status'] != 'complete':
            raise SystemExit('Provider unavailable or output validation failed. Existing translations were kept.')
        (languages.BASE / f'{code}.json').write_text(json.dumps(result['translations'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__': asyncio.run(main())
