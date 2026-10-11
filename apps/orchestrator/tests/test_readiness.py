from test_staff_presence import client
import support
import security

def test_database_readiness_is_read_only(monkeypatch,tmp_path):
    missing=tmp_path/'missing.db'
    monkeypatch.setattr(support,'DB',missing)
    response=client.get('/health')
    assert response.status_code==503
    assert response.json()['database_ready'] is False
    assert not missing.exists()

def test_host_recovery_does_not_create_missing_database(tmp_path):
    import sqlite3
    import pytest
    with pytest.raises(sqlite3.OperationalError):
        security.reset_super_admin_mfa(tmp_path)
    assert not (tmp_path/'support.db').exists()
