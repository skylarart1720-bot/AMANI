"""Report configuration and live provider availability without displaying secrets."""
import asyncio
import json
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

async def main():
    key = os.getenv('OPENAI_API_KEY') or os.getenv('LLM_API_KEY')
    async with httpx.AsyncClient(timeout=30) as client:
        if key:
            response = await client.post(os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/') + '/chat/completions', headers={'Authorization': 'Bearer ' + key},
                json={'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'), 'store': False, 'max_completion_tokens': 20,
                      'messages': [{'role': 'user', 'content': 'Reply with the word connected.'}]})
            code = response.json().get('error', {}).get('code') if not response.is_success else None
            print('AI provider:', 'LIVE' if response.is_success else f'FAILED (HTTP {response.status_code}; {code})')
        else:
            print('AI provider: NOT CONFIGURED')
        manifest = ROOT / '.runtime/services.json'
        if manifest.exists():
            services = {item['name']: item['url'] for item in json.loads(manifest.read_text())}
            response = await client.post(services['scanner'] + '/check', json={'url': 'https://example.com/', 'consent': True})
            if response.is_success:
                result = response.json()
                print('Reputation verdict:', result['verdict'])
                for provider in result['providers']:
                    print(provider['provider'] + ': ' + provider['status'])
                if not result['providers']:
                    print('Reputation providers: NOT CONFIGURED')
            else:
                print('Reputation service: FAILED', response.status_code)
            gateway = await client.get(services['whatsapp'] + '/health')
            print('WhatsApp:', 'CONFIGURED (delivery requires Meta onboarding)' if gateway.json()['configured'] else 'NOT CONFIGURED')

if __name__ == '__main__':
    asyncio.run(main())
