# Quick Start: Local PostgreSQL with pgvector

## 🚀 Fastest Way (Using Docker - Recommended)

### Prerequisites
1. **Install Docker Desktop**: https://www.docker.com/products/docker-desktop/
   - Download and install
   - Restart your computer
   - Make sure Docker Desktop is running (icon in system tray)

### Step-by-Step Commands

**1. Start PostgreSQL:**
```powershell
docker compose up -d
```

**2. Wait 10 seconds, then verify:**
```powershell
docker ps
```

**3. Create .env file:**
```powershell
@"
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agentic_rag
"@ | Out-File -FilePath .env -Encoding utf8
```

**4. Initialize database:**
```powershell
python init_database.py
```

**5. Verify it works:**
```powershell
python -c "import asyncio; from agent.db_utils import test_connection; print('✅ Success!' if asyncio.run(test_connection()) else '❌ Failed')"
```

**Done!** Your database is ready. 🎉

---

## 📋 What Each Command Does

- `docker compose up -d` - Starts PostgreSQL in background
- `docker ps` - Shows running containers
- `python init_database.py` - Creates tables and enables pgvector
- The test command - Verifies connection works

---

## 🛠 Useful Commands

**Stop database:**
```powershell
docker compose down
```

**Start database:**
```powershell
docker compose up -d
```

**View logs:**
```powershell
docker logs agentic-rag-postgres
```

**Reset everything:**
```powershell
docker compose down -v
docker compose up -d
python init_database.py
```

---

## ❌ Troubleshooting

**"docker: command not found"**
→ Install Docker Desktop and restart your computer

**"port 5432 already in use"**
→ Edit `docker-compose.yml`, change `"5432:5432"` to `"5433:5432"`
→ Update `.env`: `DATABASE_URL=postgresql://postgres:postgres@localhost:5433/agentic_rag`

**"Connection refused"**
→ Wait 15 seconds after `docker compose up -d`
→ Check Docker Desktop is running
→ Run `docker ps` to see if container is running

