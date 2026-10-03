import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / 'apps' / 'orchestrator' / 'src'
sys.path.insert(0, str(SRC_DIR))

import main


class KnowledgeRetrievalTests(unittest.TestCase):
    def test_score_knowledge_match_prefers_title_and_tag_matches(self):
        article = {
            'id': 'chraj-rights-guide',
            'title': 'CHRAJ rights guidance',
            'summary': 'Rights-based guidance for civic freedoms and detention concerns.',
            'category': 'protest-rights',
            'source': 'CHRAJ',
            'source_url': 'https://chraj.gov.gh/',
            'verified_at': '2026-09-10',
            'tags': 'rights, civic freedom, detention, legal aid, ghana',
        }

        score = main.score_knowledge_match(article, 'detained rights legal aid')

        self.assertGreater(score, 0)
        self.assertGreater(score, main.score_knowledge_match(article, 'unknown topic'))

    def test_score_knowledge_match_gives_more_points_to_source_url(self):
        article = {
            'id': 'ghana-mental-health-authority',
            'title': 'Ghana Mental Health Authority',
            'summary': 'Official guidance and crisis support pathways for mental health, distress, and wellbeing support in Ghana.',
            'category': 'mental-health',
            'source': 'Ghana Mental Health Authority',
            'source_url': 'https://mha.gov.gh/',
            'verified_at': '2026-09-10',
            'tags': 'mental health, crisis, wellbeing, ghana',
        }

        score = main.score_knowledge_match(article, 'mental health crisis')

        self.assertGreater(score, 0)

    def test_score_knowledge_match_handles_missing_source_url(self):
        article = {
            'id': 'legacy-article',
            'title': 'Legacy support article',
            'summary': 'Guidance for online safety and account recovery.',
            'category': 'digital-rights',
            'source': 'Legacy referral source',
            'source_url': None,
            'verified_at': '2026-09-10',
            'tags': 'online safety, recovery',
        }

        score = main.score_knowledge_match(article, 'online safety')

        self.assertGreater(score, 0)

    def test_build_contextual_reply_includes_source_url(self):
        article = {
            'id': 'ghana-mental-health-authority',
            'title': 'Ghana Mental Health Authority',
            'summary': 'Official guidance and crisis support pathways for mental health, distress, and wellbeing support in Ghana.',
            'category': 'mental-health',
            'source': 'Ghana Mental Health Authority',
            'source_url': 'https://mha.gov.gh/',
            'verified_at': '2026-09-10',
            'tags': 'mental health, crisis, wellbeing, ghana',
        }

        reply = main.build_contextual_reply('I feel unsafe', 'mental-health', [article])

        self.assertIn('https://mha.gov.gh/', reply)


if __name__ == '__main__':
    unittest.main()
