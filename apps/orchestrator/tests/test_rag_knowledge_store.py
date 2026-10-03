import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / 'apps' / 'orchestrator' / 'src'
sys.path.insert(0, str(SRC_DIR))

import main


class RAGKnowledgeStoreTests(unittest.TestCase):
    def test_trusted_source_registry_has_expected_sources(self):
        source_ids = {source['id'] for source in main.TRUSTED_SOURCES}
        self.assertIn('amnesty-international', source_ids)
        self.assertIn('chraj', source_ids)
        self.assertIn('ghana-mental-health-authority', source_ids)

    def test_build_rag_context_includes_source_url_and_summary(self):
        context = main.build_rag_context([
            {
                'title': 'Ghana Mental Health Authority',
                'source': 'Ghana Mental Health Authority',
                'source_url': 'https://mha.gov.gh/',
                'summary': 'Official guidance and crisis support pathways for mental health, distress, and wellbeing support in Ghana.',
                'verified_at': '2026-09-10',
            }
        ])

        self.assertIn('https://mha.gov.gh/', context)
        self.assertIn('Official guidance', context)


if __name__ == '__main__':
    unittest.main()
