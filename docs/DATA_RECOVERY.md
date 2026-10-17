# NutriMenu AI — Data Protection, Backup & Disaster Recovery Guide

This operational manual documents data retention rules, backup procedures, restoration verification, and the disaster recovery strategy for NutriMenu AI.

---

## 1. Data Ownership & Retention Policies

| Entity | Storage | Owner | Retention Policy | Cascading Deletion Behavior |
|---|---|---|---|---|
| **User Identity** | `users` table | User | Active until explicit deletion | Cascades to profile, meals, menus, sessions, and codes |
| **Health Profile** | `user_profiles` table | User | Retained while user active | Deleted immediately upon user account purge |
| **Logged Meals** | `logged_meals` table | User | Retained indefinitely | Exportable as CSV; deleted with user account |
| **Saved Menus** | `saved_menus` table | User | Retained indefinitely | Triggers deletion of associated image on disk/S3 |
| **Menu Image Files** | `uploads/menus/` | User | Linked to SavedMenu | Unlinked and deleted during menu deletion or account purge |
| **Sessions** | `sessions` table | User / Device | 7 days idle, 30 days absolute | Auto-cleaned after 30 days via `run_maintenance_cycle` |
| **Security Audit Logs** | `audit_logs` table | System / User | 180 days default | Retained for auditability; user_id set to NULL if user deleted |
| **Rate Limit Buckets** | `rate_limit_buckets` | IP / Key | 1 hour window | Auto-pruned during routine maintenance cycles |

---

## 2. Disaster Recovery Objectives

- **Recovery Point Objective (RPO)**: <= 1 hour (Automated snapshot frequency).
- **Recovery Time Objective (RTO)**: <= 15 minutes (Database restoration and service startup).

---

## 3. Automated Backup Procedure

### Local Development / SQLite Backup
To create an atomic, non-locking backup of the SQLite database:
```bash
python -c "
import sqlite3, shutil, datetime
now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
src = sqlite3.connect('nutrimenu.db')
dst = sqlite3.connect(f'backups/nutrimenu_backup_{now}.db')
with dst:
    src.backup(dst)
dst.close()
src.close()
print(f'Backup complete: backups/nutrimenu_backup_{now}.db')
"
```

### Production PostgreSQL Backup
In production environments (Neon, Supabase, AWS RDS):
```bash
# Full compressed SQL dump with table schemas and indexes
pg_dump -Fc --no-acl --no-owner $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).dump

# Encrypt backup archive with AES-256 before offsite replication
gpg --symmetric --cipher-algo AES256 backup_*.dump
```

### Uploaded File Storage Backup
Uploaded menu images in `uploads/menus/` should be synchronized to an encrypted, versioned object store:
```bash
# Sync local uploads directory to offsite backup bucket
aws s3 sync uploads/ s3://nutrimenu-backups-secure/uploads/ --sse aws:kms
```

---

## 4. Restoration & Verification Procedure

In an isolated recovery environment:
1. Provision a clean database container or instance.
2. Restore database:
   ```bash
   pg_restore --clean --if-exists -d $TEST_RESTORE_DB_URL backup_file.dump
   ```
3. Run verification check to confirm data integrity:
   ```bash
   python -c "
   from backend.database import SessionLocal
   from backend.db_models import User, SavedMenu, LoggedMeal
   db = SessionLocal()
   print('Restored Users:', db.query(User).count())
   print('Restored Menus:', db.query(SavedMenu).count())
   print('Restored Meals:', db.query(LoggedMeal).count())
   db.close()
   "
   ```
4. Verify that foreign key relationships, profile biometrics, and file references resolve properly.

---

## 5. Account Deletion & Privacy (GDPR Compliance)
- When a user requests deletion via `/api/auth/account` or `/api/account/deletion/request`, the account enters a **14-day grace period** (`deletion_requested_at = now()`).
- All active sessions are immediately revoked to prevent unauthorized access.
- Users can cancel deletion at any point during the 14 days by signing in and confirming restoration.
- Once the 14 days expire, `run_maintenance_cycle()` permanently deletes the user record, cascades through all database tables, and unlinks all uploaded image files from disk.
