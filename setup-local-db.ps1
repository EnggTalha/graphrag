# PowerShell script for setting up local PostgreSQL with pgvector on Windows

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setting up Local PostgreSQL with pgvector" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
try {
    docker --version | Out-Null
    Write-Host "✅ Docker is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "   Visit: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Start PostgreSQL container
Write-Host "🚀 Starting PostgreSQL container..." -ForegroundColor Yellow
try {
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        docker-compose up -d
    }
} catch {
    Write-Host "❌ Failed to start Docker container" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "⏳ Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Wait for PostgreSQL to be healthy
$maxAttempts = 30
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts) {
    try {
        docker exec agentic-rag-postgres pg_isready -U postgres 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ PostgreSQL is ready!" -ForegroundColor Green
            $ready = $true
            break
        }
    } catch {
        # Continue waiting
    }
    $attempt++
    Write-Host "   Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Write-Host "❌ PostgreSQL failed to start. Check logs with: docker logs agentic-rag-postgres" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🔧 Verifying pgvector extension..." -ForegroundColor Yellow
try {
    docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1 | Out-Null
    Write-Host "✅ pgvector extension is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create pgvector extension" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Local PostgreSQL with pgvector is ready!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Connection details:" -ForegroundColor Yellow
Write-Host "  Host: localhost"
Write-Host "  Port: 5432"
Write-Host "  Database: agentic_rag"
Write-Host "  Username: postgres"
Write-Host "  Password: postgres"
Write-Host ""
Write-Host "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agentic_rag" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Create a .env file with the DATABASE_URL above"
Write-Host "  2. Run: python init_database.py"
Write-Host "  3. Run: python -m ingestion.ingest"
Write-Host ""
Write-Host "To stop the database:" -ForegroundColor Yellow
Write-Host "  docker compose down"
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Yellow
Write-Host "  docker logs agentic-rag-postgres"
Write-Host ""

