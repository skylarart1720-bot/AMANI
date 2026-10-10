# Encrypted backup and recovery

The orchestrator image includes `python -m src.backup`. Locally use `.\.venv\Scripts\python.exe scripts/backup-support.py`. Backups contain SQLite snapshots of `support.db` and any `whatsapp.db`/`amani_line.db` found in the chosen data directory. Staff accounts, conversations, private notes, feedback, directory, knowledge and service settings in these databases are included. Runtime translation caches and uploaded/source files outside these databases need separate copies.

## Keys and storage

Set `AMANI_BACKUP_KEY` privately to a Fernet key distinct from the existing `CHAT_ENCRYPTION_KEY`. Generate it once with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` in a private terminal. Store both keys in a separate secret manager. Never commit keys or backups. Changing either key without retaining the original prevents recovery of earlier backups. The existing admin token is not exported and must remain available in Railway configuration.

The tool encrypts the entire archive, including account hashes and legacy databases. It never includes environment files or keys. Keep backup copies off the database host with restricted access and an explicit retention period; the active seven-day conversation deletion policy does not delete unmanaged backup copies. Restore can bring back previously deleted conversations: review retention/deletion records before restarting a restored service.

## Create a snapshot

On Railway, execute inside the orchestrator service/container with its persistent volume mounted and the two key variables configured:

```sh
python -m src.backup create --data-dir /data --output /backups/amani-2026-10-10.amani-backup
```

Use a unique filename each time. SQLite's backup API permits a consistent snapshot while the API is running. Separate databases are copied sequentially, so stop gateway/API writers for a coordinated cross-service recovery point. If the gateway volume is separate, take its snapshot from the host where that database is accessible. Copy the resulting archive off-host and verify the copy with an isolated restore. `/backups` must be persistent if it is used for storage; no new volume or hosted schedule is configured automatically.

Local equivalent:

```powershell
.\.venv\Scripts\python.exe scripts/backup-support.py create --data-dir data --output backups/amani-example.amani-backup
```

## Validate and restore safely

```sh
python -m src.backup restore --input /backups/amani-2026-10-10.amani-backup --destination /data-restored
```

The destination must be empty. The tool verifies archive authentication, expected filenames, encryption-key fingerprint, checksums, SQLite integrity and foreign keys before writing restored databases. It refuses to replace existing data. Staff sessions and presence are cleared; users must sign in again. Visitor session hashes and encrypted conversations are preserved.

For a production cutover: stop API and gateway writers, preserve a fresh snapshot of the current data, restore into a separate persistent directory, inspect records using the same chat key, review retention/deletion requirements, then point services at the recovered directories and restart. Verify health, Super Admin/staff login, case routing, history, notes and feedback. Preserve the previous directory for rollback under the agreed retention policy. Do not overwrite an active SQLite file or change the chat encryption key.

## Routine operation

Assign an owner for daily snapshots, off-host copies, retention cleanup and periodic isolated restore drills. The command is suitable for a host scheduler, but hosted scheduling/secret configuration requires access to the host and is still an operational setup task. Monitor command failures and backup age. A local synthetic restore test does not establish a production recovery-time guarantee.
