"""Encrypted SQLite snapshots. Restore only into a new, empty directory."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from zipfile import ZipFile
from cryptography.fernet import Fernet

DATABASES = ('support.db', 'whatsapp.db', 'amani_line.db')

def fingerprint(chat_key):
    return hashlib.sha256(chat_key.encode()).hexdigest()

def check_db(path):
    with closing(sqlite3.connect(path)) as conn:
        if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed')
        if conn.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Database foreign-key check failed')

def create_backup(data_dir, output, backup_key, chat_key):
    if backup_key == chat_key:
        raise ValueError('Use a separate backup encryption key')
    data_dir, output = Path(data_dir), Path(output)
    if output.exists():
        raise ValueError('Choose a new backup filename')
    cipher = Fernet(backup_key.encode())
    Fernet(chat_key.encode())
    files = {}
    with tempfile.TemporaryDirectory() as temporary:
        for name in DATABASES:
            source = data_dir / name
            if not source.is_file():
                continue
            snapshot = Path(temporary) / name
            with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro', uri=True)) as src, closing(sqlite3.connect(snapshot)) as dest:
                src.backup(dest)
            check_db(snapshot)
            files[name] = snapshot.read_bytes()
    if 'support.db' not in files:
        raise ValueError('support.db was not found')
    manifest = {'version':1,'created_utc':datetime.now(timezone.utc).isoformat(), 'chat_key_fingerprint':fingerprint(chat_key),
                'files':{name:hashlib.sha256(value).hexdigest() for name,value in files.items()}}
    buffer = io.BytesIO()
    with ZipFile(buffer,'w') as archive:
        archive.writestr('manifest.json',json.dumps(manifest))
        for name,value in files.items():
            archive.writestr(name,value)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as destination:
        destination.write(cipher.encrypt(buffer.getvalue()))
    return manifest

def restore_backup(source, destination, backup_key, chat_key):
    destination = Path(destination)
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Restore destination must be an empty directory')
    plain = Fernet(backup_key.encode()).decrypt(Path(source).read_bytes())
    with ZipFile(io.BytesIO(plain)) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('version') != 1 or manifest.get('chat_key_fingerprint') != fingerprint(chat_key):
            raise ValueError('Backup version or chat encryption key does not match')
        files = manifest.get('files',{})
        if 'support.db' not in files or set(files)-set(DATABASES) or set(archive.namelist()) != {'manifest.json',*files}:
            raise ValueError('Unexpected backup contents')
        with tempfile.TemporaryDirectory() as temporary:
            for name,digest in files.items():
                value = archive.read(name)
                if hashlib.sha256(value).hexdigest() != digest:
                    raise ValueError('Backup checksum mismatch')
                snapshot = Path(temporary)/name
                snapshot.write_bytes(value)
                check_db(snapshot)
            # Restored staff must sign in again; saved presence never survives recovery.
            with closing(sqlite3.connect(Path(temporary)/'support.db')) as conn:
                tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for table in ('staff_sessions','staff_presence'):
                    if table in tables:
                        conn.execute('DELETE FROM '+table)
                conn.commit()
            destination.mkdir(parents=True,exist_ok=True)
            written=[]
            try:
                for name in files:
                    target=destination/name
                    with target.open('xb') as output:
                        output.write((Path(temporary)/name).read_bytes())
                    written.append(target)
            except Exception:
                for target in written:
                    target.unlink()
                raise
    return manifest

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    create=sub.add_parser('create'); create.add_argument('--data-dir',default=os.getenv('AMANI_DATA_DIR','/data'));create.add_argument('--output',required=True)
    restore=sub.add_parser('restore');restore.add_argument('--input',required=True);restore.add_argument('--destination',required=True)
    args=parser.parse_args()
    backup_key=os.getenv('AMANI_BACKUP_KEY','');chat_key=os.getenv('CHAT_ENCRYPTION_KEY','')
    if not backup_key or not chat_key:
        parser.error('Set AMANI_BACKUP_KEY and CHAT_ENCRYPTION_KEY through private environment settings')
    try:
        if args.command=='create':
            result=create_backup(args.data_dir,args.output,backup_key,chat_key)
        else:
            result=restore_backup(args.input,args.destination,backup_key,chat_key)
    except Exception as error:
        raise SystemExit('Backup operation failed: '+type(error).__name__) from None
    print('PASS: '+args.command+'; verified databases: '+', '.join(result['files']))

if __name__=='__main__':
    main()
