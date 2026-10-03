import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / 'apps' / 'orchestrator' / 'src'
sys.path.insert(0, str(SRC_DIR))

import approved_source_connector


class ApprovedSourceConnectorTests(unittest.TestCase):
    def test_build_source_record_from_pdf(self):
        temp_dir = Path(__file__).resolve().parent
        pdf_path = temp_dir / 'approved_rights_guide.pdf'
        pdf_path.write_bytes(b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF')

        try:
            record = approved_source_connector.build_source_record(
                pdf_path,
                source_name='Trusted Rights Desk',
                category='protest-rights',
                source_url='https://example.org/rights-guide',
                tags='rights, legal aid',
            )

            self.assertEqual(record['title'], 'approved rights guide')
            self.assertEqual(record['source'], 'Trusted Rights Desk')
            self.assertEqual(record['category'], 'protest-rights')
            self.assertEqual(record['source_url'], 'https://example.org/rights-guide')
        finally:
            if pdf_path.exists():
                pdf_path.unlink()

    def test_build_source_record_uses_url_metadata_when_available(self):
        record = approved_source_connector.build_source_record(
            url='https://example.org/approved-guide',
            source_name='Approved Web Desk',
            category='digital-rights',
            tags='online safety',
        )

        self.assertEqual(record['source'], 'Approved Web Desk')
        self.assertEqual(record['category'], 'digital-rights')
        self.assertEqual(record['source_url'], 'https://example.org/approved-guide')
        self.assertIsInstance(record['summary'], str)
