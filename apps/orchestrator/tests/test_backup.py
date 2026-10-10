import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from cryptography.fernet import Fernet, InvalidToken
from backup import create_backup,restore_backup

def test_encrypted_backup_round_trip_and_safe_restore(tmp_path):
    data=tmp_path/'data';data.mkdir()
    with sqlite3.connect(data/'support.db') as conn:
        conn.executescript("CREATE TABLE staff_accounts(id TEXT); INSERT INTO staff_accounts VALUES('example'); CREATE TABLE staff_sessions(id TEXT); INSERT INTO staff_sessions VALUES('expired'); CREATE TABLE staff_presence(id TEXT); INSERT INTO staff_presence VALUES('online'); CREATE TABLE support_settings(hours TEXT); INSERT INTO support_settings VALUES('Example hours');")
    key=Fernet.generate_key().decode();chat=Fernet.generate_key().decode()
    with sqlite3.connect(data/'support.db') as conn:
        conn.execute('CREATE TABLE messages(content TEXT)')
        conn.execute('INSERT INTO messages VALUES(?)',(Fernet(chat.encode()).encrypt(b'Synthetic conversation').decode(),))
    output=tmp_path/'snapshot.amani-backup'
    manifest=create_backup(data,output,key,chat)
    assert b'Example hours' not in output.read_bytes()
    restored=tmp_path/'restored'
    restore_backup(output,restored,key,chat)
    with sqlite3.connect(restored/'support.db') as conn:
        assert conn.execute('SELECT id FROM staff_accounts').fetchone()[0]=='example'
        assert conn.execute('SELECT hours FROM support_settings').fetchone()[0]=='Example hours'
        assert conn.execute('SELECT COUNT(*) FROM staff_sessions').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM staff_presence').fetchone()[0]==0
        assert Fernet(chat.encode()).decrypt(conn.execute('SELECT content FROM messages').fetchone()[0].encode())==b'Synthetic conversation'
    with pytest.raises(ValueError):restore_backup(output,restored,key,chat)
    with pytest.raises(ValueError):restore_backup(output,tmp_path/'wrong-chat',key,Fernet.generate_key().decode())
    with pytest.raises(InvalidToken):restore_backup(output,tmp_path/'wrong-backup',Fernet.generate_key().decode(),chat)
    assert not (tmp_path/'wrong-chat').exists()
    assert manifest['files'].keys()=={'support.db'}
    with pytest.raises(ValueError):create_backup(data,output,key,chat)
