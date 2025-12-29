"""
Initialize database schema without psql.
Run this to set up your database tables.
"""

import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def init_database():
    """Initialize database with schema.sql"""
    
    # Get database URL from .env
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in .env file")
        return False
    
    print("🔗 Connecting to database...")
    print(f"   URL: {database_url[:50]}...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected successfully!")
        
        # Read schema.sql
        schema_path = Path(__file__).parent / "sql" / "schema.sql"
        
        if not schema_path.exists():
            print(f"❌ ERROR: schema.sql not found at {schema_path}")
            await conn.close()
            return False
        
        print(f"📄 Reading schema from: {schema_path}")
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("🔧 Executing schema SQL...")
        print("   This will create tables: documents, chunks, sessions, messages")
        
        # Execute the schema
        await conn.execute(schema_sql)
        
        print("✅ Database schema initialized successfully!")
        
        # Verify tables were created
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        
        print(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"   ✓ {table['tablename']}")
        
        await conn.close()
        print("\n🎉 Database is ready!")
        return True
        
    except asyncpg.PostgresError as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Database Initialization Script")
    print("=" * 60)
    print()
    
    success = asyncio.run(init_database())
    
    if success:
        print("\n✅ Ready for next step: Document ingestion")
        print("   Run: python -m ingestion.ingest --verbose --clean")
    else:
        print("\n❌ Failed to initialize database")
        print("   Check your DATABASE_URL in .env file")

