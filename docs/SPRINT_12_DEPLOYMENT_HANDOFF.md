# SPRINT 12 — DEPLOYMENT, PERSISTENCE & DISASTER RECOVERY
**Full-Stack Evidence-Grounded Clinical AI Chatbot Agent**  
**Rumah Sakit Umum Kota Terpadu (RSUKT)**

---

## 1. Executive Summary & Deployment Architecture
Sprint 12 formalizes the deployment handoff, persistence guarantees, disaster recovery runbooks, and zero-downtime operational procedures for both bare-metal Windows environments and containerized Docker clusters.

---

## 2. Persistence Architecture
- **Primary Data Store**: `database/clinical_agent.db` running in SQLite Write-Ahead Logging (`WAL`) mode with `synchronous = NORMAL` and `foreign_keys = ON`.
- **Vector Embeddings Store**: `vec_chunks` SQLite virtual table powered by `sqlite-vec`.
- **Dataset Storage**: `datasets/` hierarchy preserving raw, approved, quarantined, and exported files.
- **Model Registry Storage**: `models/registry/` storing versioned pickle artifacts and model cards.

---

## 3. Disaster Recovery Runbook
1. **Trigger Manual Snapshot**:
   ```cmd
   .\services\ai-api\.venv\Scripts\python.exe -c "from app.security.backup import create_database_backup; print(create_database_backup())"
   ```
2. **Scheduled Automated Backup**:
   Snapshots are taken automatically to `database/backups/clinical_agent_backup_YYYYMMDD_HHMMSS.db` accompanied by `.sha256` files.
3. **Database Restoration**:
   To recover from disaster or rollback corrupt state:
   ```python
   from app.security.backup import restore_database_backup
   restore_database_backup(Path("database/backups/clinical_agent_backup_20261024_023535.db"))
   ```

---

## 4. Operational Sign-Off
All services (FastAPI on Port 8000, Next.js on Port 3000) are verified operational and loadable via [`start_all.bat`](file:///c:/Users/user/RAG-model-record/start_all.bat) and [`docker-compose.yml`](file:///c:/Users/user/RAG-model-record/docker-compose.yml).
