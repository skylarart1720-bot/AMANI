import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / 'apps' / 'orchestrator' / 'src'
sys.path.insert(0, str(SRC_DIR))

import main


class KnowledgeIngestionTests(unittest.TestCase):
    def test_upsert_knowledge_article_keeps_required_fields(self):
        article = {
            'id': 'test-ingest-article',
            'title': 'Trusted rights guidance',
            'summary': 'Support and legal guidance for people facing harassment.',
            'category': 'digital-rights',
            'source': 'Trust and Safety Desk',
            'source_url': 'https://example.org/rights-guidance',
            'verified_at': '2026-09-11',
            'tags': 'rights, harassment, support',
        }

        saved = main.upsert_knowledge_article(article)

        self.assertEqual(saved['id'], article['id'])
        self.assertEqual(saved['source'], article['source'])
        self.assertIn('https://example.org/rights-guidance', saved['source_url'])

    def test_batch_ingest_knowledge_articles(self):
        articles = [
            {
                'id': 'batch-ingest-1',
                'title': 'Mental health support guidance',
                'summary': 'Crisis support and wellbeing guidance for mental health concerns.',
                'category': 'mental-health',
                'source': 'Ghana Mental Health Authority',
                'source_url': 'https://mha.gov.gh/support',
                'verified_at': '2026-09-11',
                'tags': 'mental health, crisis, support',
            },
            {
                'id': 'batch-ingest-2',
                'title': 'Digital safety basics',
                'summary': 'Online safety basics for evidence preservation and account recovery.',
                'category': 'digital-rights',
                'source': 'Digital Rights Desk',
                'source_url': 'https://example.org/digital-safety',
                'verified_at': '2026-09-11',
                'tags': 'digital safety, account recovery',
            },
        ]

        saved = main.batch_ingest_knowledge_articles(articles)

        self.assertEqual(len(saved), 2)
        self.assertEqual({item['id'] for item in saved}, {'batch-ingest-1', 'batch-ingest-2'})

    def test_review_workflow_approves_article_for_live_retrieval(self):
        submission = {
            'title': 'Community legal aid desk guidance',
            'summary': 'How to access legal aid and document rights violations safely.',
            'category': 'protest-rights',
            'source': 'Legal Aid Desk',
            'source_url': 'https://example.org/legal-aid',
            'verified_at': '2026-09-11',
            'tags': 'legal aid, rights, protest support',
        }

        review = main.create_source_review(submission)
        self.assertEqual(review['status'], 'pending')

        approved = main.approve_source_review(review['id'], reviewer='moderator-test')
        self.assertEqual(approved['status'], 'approved')

        live = main.fetch_knowledge_articles('legal aid desk', limit=5)
        self.assertTrue(any(item['title'] == 'Community legal aid desk guidance' for item in live))

    def test_pdf_document_intake_extracts_and_chunks_content(self):
        pdf_path = PROJECT_ROOT / 'Amani_Line_Rights_Support_System_Blueprint.pdf'
        if not pdf_path.exists():
            self.skipTest('Blueprint PDF is not present in the workspace.')

        text = main.extract_pdf_text(pdf_path)
        self.assertGreater(len(text), 200)
        self.assertIn('Amani', text)

        chunks = main.chunk_text(text)
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(len(chunk) > 0 for chunk in chunks))

        intake = main.ingest_pdf_document(pdf_path, source_name='Blueprint PDF', category='digital-rights')
        self.assertEqual(intake['status'], 'pending')
        self.assertIn('Blueprint', intake['title'])

    def test_approved_review_chunks_are_published_as_live_knowledge(self):
        submission = {
            'title': 'Community support guidance',
            'summary': 'Guidance for support, safety, and referrals in crisis situations.',
            'category': 'mental-health',
            'source': 'Community wellbeing desk',
            'source_url': 'https://example.org/community-support',
            'verified_at': '2026-09-11',
            'tags': 'wellbeing, support, crisis',
            'chunks': [
                'Immediate support should include checking if the person is safe and calling a trusted contact.',
                'If there is immediate danger, contact emergency services and keep the person with a trusted adult.',
            ],
        }

        review = main.create_source_review(submission)
        approved = main.approve_source_review(review['id'], reviewer='moderator-test')
        published = main.publish_approved_review(review['id'])

        self.assertEqual(approved['status'], 'approved')
        self.assertEqual(published['status'], 'published')

        live = main.fetch_knowledge_articles('support and crisis', limit=5)
        self.assertTrue(any(item['title'] == 'Community support guidance' for item in live))

    def test_review_queue_tracks_pending_and_rejected_state(self):
        submission = {
            'title': 'Youth wellbeing outreach guidance',
            'summary': 'Guidance for youth wellbeing access, referral, and trauma aware support.',
            'category': 'mental-health',
            'source': 'Youth wellbeing desk',
            'source_url': 'https://example.org/youth-wellbeing',
            'verified_at': '2026-09-11',
            'tags': 'youth, wellbeing, support',
        }

        review = main.create_source_review(submission)
        queue = main.fetch_review_queue(status='pending')
        self.assertTrue(any(item['id'] == review['id'] for item in queue))

        rejected = main.reject_source_review(review['id'], reviewer='moderator-test', notes='Needs source validation.')
        self.assertEqual(rejected['status'], 'rejected')

    def test_mental_health_queries_rank_curated_wellbeing_sources_above_legacy_legal_content(self):
        legacy = {
            'id': 'legacy-mental-ranking',
            'title': 'Amani rights legal aid desk review 2026',
            'summary': 'Support for stress, depression, and overwhelming situations, with guidance on legal and rights referrals.',
            'category': 'protest-rights',
            'source': 'Amani Legal Aid Desk Unique Trust Check',
            'source_url': 'https://example.org/legacy-review',
            'verified_at': '2026-09-11',
            'tags': 'legal aid, rights, support, depression, stress',
        }
        curated = {
            'id': 'curated-mental-ranking',
            'title': 'mental health support pathways',
            'summary': 'Crisis support, wellbeing guidance, and immediate steps for depression, overwhelming stress, and emotional safety.',
            'category': 'mental-health',
            'source': 'Ghana Mental Health Authority',
            'source_url': 'https://mha.gov.gh/support',
            'verified_at': '2026-09-11',
            'tags': 'mental health, crisis, wellbeing, depression, stress',
        }

        main.upsert_knowledge_article(legacy)
        main.upsert_knowledge_article(curated)

        matches = main.fetch_knowledge_articles('I am feeling overwhelmed and depressed', limit=5)
        self.assertTrue(matches[0]['id'] == 'curated-mental-ranking')
        self.assertLess(main.score_knowledge_match(legacy, 'I am feeling overwhelmed and depressed'), main.score_knowledge_match(curated, 'I am feeling overwhelmed and depressed'))

    def test_publish_review_endpoint_makes_approved_content_live(self):
        review = main.create_source_review({
            'title': 'Moderator published legal aid guidance',
            'summary': 'Approved guidance for safe legal aid and evidence preservation.',
            'category': 'protest-rights',
            'source': 'Moderator Verified Legal Desk',
            'source_url': 'https://example.org/moderator-legal-guide',
            'verified_at': '2026-09-11',
            'tags': 'legal aid, rights, evidence',
        })

        main.approve_source_review(review['id'], reviewer='moderator-publish', notes='Verified by policy team.')
        published = main.publish_review_endpoint(review['id'])

        self.assertEqual(published['status'], 'published')
        self.assertTrue(any(item['title'] == 'Moderator published legal aid guidance' for item in main.fetch_knowledge_articles('legal aid evidence', limit=10)))

    def test_approved_source_ingestion_creates_review_queue_entries(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / 'approved_guide.txt'
            source_path.write_text('A trusted legal aid guide for protest support and evidence preservation.', encoding='utf-8')

            batch = main.ingest_approved_sources([{
                'title': 'Externally approved legal aid guide',
                'summary': 'Approved reference for safe legal aid and rights guidance.',
                'category': 'protest-rights',
                'source': 'External rights desk',
                'source_url': 'https://example.org/external-rights-guide',
                'verified_at': '2026-09-11',
                'tags': 'legal aid, rights, support',
                'content_path': str(source_path),
            }])

        self.assertTrue(len(batch) >= 1)
        self.assertTrue(all(item['status'] == 'pending' for item in batch))
        self.assertTrue(any(item['title'] == 'Externally approved legal aid guide' for item in batch))

    def test_approved_source_api_creates_pending_review_items(self):
        import support
        response = main.app.test_client().post('/approved-sources', headers={'Authorization': 'Bearer ' + support.ADMIN_TOKEN}, json={
            'title': 'API approved legal aid guide',
            'summary': 'Approved guidance for safe legal aid and rights support.',
            'category': 'protest-rights',
            'source': 'API rights desk',
            'source_url': 'https://example.org/api-rights-guide',
            'verified_at': '2026-09-11',
            'tags': 'legal aid, rights, support',
        })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(isinstance(payload, list))
        self.assertEqual(payload[0]['status'], 'pending')
        self.assertEqual(payload[0]['title'], 'API approved legal aid guide')

    def test_approved_source_url_intake_extracts_title_and_summary(self):
        import http.server
        import socketserver
        import threading

        html = b"""
        <html>
          <head><title>Community Legal Aid & Rights Notice</title></head>
          <body>
            <h1>Approved legal aid guidance</h1>
            <p>Safe legal aid and evidence preservation advice for crisis support and protest rights.</p>
          </body>
        </html>
        """

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args, **kwargs):
                pass

            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html)

        with socketserver.TCPServer(('127.0.0.1', 0), QuietHandler) as server:
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            batch = main.ingest_approved_sources([{ 
                'source': 'Approved web source',
                'source_url': f'http://127.0.0.1:{port}/guide',
                'category': 'protest-rights',
                'verified_at': '2026-09-11',
                'tags': 'legal aid, rights, support',
            }])
            server.shutdown()
            thread.join(timeout=5)

        self.assertTrue(len(batch) >= 1)
        self.assertEqual(batch[0]['title'], 'Community Legal Aid & Rights Notice')
        self.assertIn('Safe legal aid', batch[0]['summary'])

    def test_trusted_source_score_and_review_history_are_tracked(self):
        review = main.create_source_review({
            'title': 'Trusted community legal aid guidance',
            'summary': 'Careful legal referral and evidence preservation advice.',
            'category': 'protest-rights',
            'source': 'Trusted Legal Aid Desk',
            'source_url': 'https://example.org/trusted-legal-aid',
            'verified_at': '2026-09-11',
            'tags': 'legal aid, rights, trust',
        })

        main.approve_source_review(review['id'], reviewer='moderator-trust', notes='Verified source.')
        main.publish_approved_review(review['id'])

        sources = main.fetch_trusted_sources()
        self.assertTrue(any(source.get('name') == 'Trusted Legal Aid Desk' for source in sources))
        self.assertTrue(any('trust_score' in source for source in sources))

        history = main.fetch_review_history(review_id=review['id'])
        self.assertTrue(len(history) >= 2)
        self.assertTrue(any(item['status'] == 'approved' for item in history))

    def test_trust_score_boosts_retrieval_priority(self):
        trusted_source_name = 'Amani Legal Aid Desk Unique Trust Check'
        low_trust_source_name = 'Local Legal Aid Desk Unique Trust Check'

        trusted = main.upsert_knowledge_article({
            'id': 'high-trust-rights-source',
            'title': 'Amani rights legal aid desk review 2026',
            'summary': 'Official legal aid desk and rights review guidance for protest support and evidence preservation.',
            'category': 'protest-rights',
            'source': trusted_source_name,
            'source_url': 'https://example.org/amani-rights-review-2026-unique',
            'verified_at': '2026-09-11',
            'tags': 'rights, legal aid, protest support, amani',
        })

        low_trust = main.upsert_knowledge_article({
            'id': 'low-trust-rights-source',
            'title': 'Local legal aid desk rights review 2026',
            'summary': 'A community legal aid desk rights review covering protest support and general guidance.',
            'category': 'protest-rights',
            'source': low_trust_source_name,
            'source_url': 'https://example.org/local-rights-review-2026-unique',
            'verified_at': '2026-09-11',
            'tags': 'rights, legal aid, protest support, local',
        })

        main._sync_source_trust_record(trusted_source_name, trusted['source_url'], trusted['category'])
        main._sync_source_trust_record(low_trust_source_name, low_trust['source_url'], low_trust['category'])

        low_trust_record = next(item for item in main.fetch_trusted_sources() if item.get('name') == low_trust_source_name)
        high_trust_record = next(item for item in main.fetch_trusted_sources() if item.get('name') == trusted_source_name)
        self.assertGreater(int(high_trust_record.get('trust_score') or 0), int(low_trust_record.get('trust_score') or 0))

        high_score = main.score_knowledge_match(trusted, 'legal aid desk rights review 2026')
        low_score = main.score_knowledge_match(low_trust, 'legal aid desk rights review 2026')
        self.assertGreater(high_score, low_score)
        self.assertGreater(high_score, 0)
        self.assertGreater(low_score, 0)

    def test_bot_reply_cites_verified_source_and_trust_level(self):
        article = {
            'id': 'transparency-source',
            'title': 'Rights and safety guide',
            'summary': 'A verified guide covering legal aid and civil rights support.',
            'category': 'protest-rights',
            'source': 'Official Rights Desk',
            'source_url': 'https://example.org/official-rights-guide',
            'verified_at': '2026-09-11',
            'tags': 'rights, support',
        }
        main._sync_source_trust_record(article['source'], article['source_url'], article['category'])

        reply = main.build_contextual_reply(
            'I need help with my arrest rights',
            'protest-rights',
            [article],
        )

        self.assertIn('Rights and safety guide', reply)
        self.assertIn('Official Rights Desk', reply)
        self.assertIn('trust', reply.lower())


if __name__ == '__main__':
    unittest.main()
