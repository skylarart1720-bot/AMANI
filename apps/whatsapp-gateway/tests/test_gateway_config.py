import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'src' / 'main.py'
spec = importlib.util.spec_from_file_location('gateway_main', MODULE_PATH)
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)


class GatewayConfigTests(unittest.TestCase):
    def test_resolve_orchestrator_url_prefers_environment_value(self):
        self.assertEqual(main.resolve_orchestrator_url('http://example.com:9000'), 'http://example.com:9000')

    def test_resolve_orchestrator_url_uses_local_default_when_missing(self):
        self.assertEqual(main.resolve_orchestrator_url(None), 'http://127.0.0.1:8005')


if __name__ == '__main__':
    unittest.main()
