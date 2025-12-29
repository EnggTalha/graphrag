#!/bin/bash

# Setup script for local PostgreSQL with pgvector

set -e

echo "=========================================="
echo "Setting up Local PostgreSQL with pgvector"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://www.docker.com/get-started"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker is installed"
echo ""

# Start PostgreSQL container
echo "🚀 Starting PostgreSQL container..."
if docker compose version &> /dev/null; then
    docker compose up -d
else
    docker-compose up -d
fi

echo ""
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Wait for PostgreSQL to be healthy
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker exec agentic-rag-postgres pg_isready -U postgres &> /dev/null; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ PostgreSQL failed to start. Check logs with: docker logs agentic-rag-postgres"
    exit 1
fi

echo ""
echo "🔧 Verifying pgvector extension..."
docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "CREATE EXTENSION IF NOT EXISTS vector;" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ pgvector extension is available"
else
    echo "❌ Failed to create pgvector extension"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Local PostgreSQL with pgvector is ready!"
echo "=========================================="
echo ""
echo "Connection details:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: agentic_rag"
echo "  Username: postgres"
echo "  Password: postgres"
echo ""
echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agentic_rag"
echo ""
echo "Next steps:"
echo "  1. Create a .env file with the DATABASE_URL above"
echo "  2. Run: python init_database.py"
echo "  3. Run: python -m ingestion.ingest"
echo ""
echo "To stop the database:"
echo "  docker compose down"
echo ""
echo "To view logs:"
echo "  docker logs agentic-rag-postgres"
echo ""

