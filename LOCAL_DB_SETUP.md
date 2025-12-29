# Local PostgreSQL with pgvector Setup Guide

This guide will help you set up a local PostgreSQL database with pgvector extension using Docker.

## Quick Start

### Option 1: Using the Setup Script (Recommended)

**On Windows (PowerShell):**
```powershell
.\setup-local-db.ps1
```

**On Linux/Mac:**
```bash
chmod +x setup-local-db.sh
./setup-local-db.sh
```

### Option 2: Manual Setup

1. **Start the PostgreSQL container:**
   ```bash
   docker compose up -d
   ```

2. **Wait for PostgreSQL to be ready** (takes about 10-15 seconds):
   ```bash
   docker logs -f agentic-rag-postgres
   ```
   Press `Ctrl+C` once you see "database system is ready to accept connections"

3. **Verify pgvector extension:**
   ```bash
   docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

## Configuration

Create a `.env` file in the project root with:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agentic_rag
```

## Initialize Database Schema

After the database is running, initialize the schema:

```bash
python init_database.py
```

This will:
- Create the `vector` extension (if not already created)
- Create all required tables (documents, chunks, sessions, messages)
- Set up indexes and functions for vector search

## Verify Installation

Test the connection:

```bash
# Using Python
python -c "import asyncio; from agent.db_utils import test_connection; print('Connected!' if asyncio.run(test_connection()) else 'Failed!')"
```

Or using psql:
```bash
docker exec -it agentic-rag-postgres psql -U postgres -d agentic_rag -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

## Database Management

### Stop the database:
```bash
docker compose down
```

### Start the database:
```bash
docker compose up -d
```

### View logs:
```bash
docker logs agentic-rag-postgres
```

### Access PostgreSQL CLI:
```bash
docker exec -it agentic-rag-postgres psql -U postgres -d agentic_rag
```

### Remove all data (fresh start):
```bash
docker compose down -v
docker compose up -d
```

## Connection Details

- **Host:** localhost
- **Port:** 5432
- **Database:** agentic_rag
- **Username:** postgres
- **Password:** postgres
- **Connection String:** `postgresql://postgres:postgres@localhost:5432/agentic_rag`

## Troubleshooting

### Port 5432 already in use

If you have PostgreSQL already running on port 5432, you can change the port in `docker-compose.yml`:

```yaml
ports:
  - "5433:5432"  # Change 5433 to any available port
```

Then update your `.env`:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/agentic_rag
```

### Container won't start

Check the logs:
```bash
docker logs agentic-rag-postgres
```

### Reset everything

To completely remove and recreate:
```bash
docker compose down -v
docker compose up -d
```

Then re-run `python init_database.py`

## Next Steps

1. ✅ Database is running
2. ✅ Schema is initialized
3. 🚀 Run document ingestion: `python -m ingestion.ingest`
4. 🚀 Start the API: `python -m agent.api`

