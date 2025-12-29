# JSON-Based Conversation Storage Guide

## Overview

The system now saves conversations in JSON files instead of PostgreSQL, making it simpler to set up and maintain. Conversations are stored locally in the `data/conversations/` directory.

## ✅ Benefits

- **No PostgreSQL Required** for conversation storage (still needed for vector search)
- **Simple File-Based Storage** - easy to backup, view, and manage
- **Human-Readable Format** - JSON files can be opened and inspected directly
- **Portable** - move conversations between systems easily
- **Version Control Friendly** - can track conversation history in git if desired

## 📁 Storage Structure

```
data/
└── conversations/
    ├── sessions.json                    # All sessions metadata
    └── conversations/
        ├── <session-id-1>.json         # Conversation 1
        ├── <session-id-2>.json         # Conversation 2
        └── ...
```

### sessions.json Format

```json
{
  "abc-123-def-456": {
    "session_id": "abc-123-def-456",
    "user_id": "user_email@example.com",
    "created_at": "2025-12-23T20:00:00",
    "updated_at": "2025-12-23T20:15:00",
    "message_count": 10,
    "metadata": {
      "project": "real-estate-qa",
      "tags": ["meeting-minutes", "properties"]
    }
  }
}
```

### Conversation File Format

```json
{
  "session_id": "abc-123-def-456",
  "messages": [
    {
      "message_id": "msg-001",
      "session_id": "abc-123-def-456",
      "role": "user",
      "content": "What projects are in our database?",
      "timestamp": "2025-12-23T20:00:00",
      "metadata": {}
    },
    {
      "message_id": "msg-002",
      "session_id": "abc-123-def-456",
      "role": "assistant",
      "content": "Based on the meeting minutes, there are several projects...",
      "timestamp": "2025-12-23T20:00:05",
      "metadata": {
        "tools_used": ["vector_search"],
        "sources": ["meetings_minutes.txt"]
      }
    }
  ]
}
```

## 🔧 How to Use

### Import the Storage Module

```python
from agent.json_storage import json_storage

# Create a session
session_id = json_storage.create_session(
    user_id="user@example.com",
    metadata={"project": "real-estate"}
)

# Add messages
json_storage.add_message(
    session_id=session_id,
    role="user",
    content="What is project PRJ-026?",
    metadata={}
)

json_storage.add_message(
    session_id=session_id,
    role="assistant",
    content="Project PRJ-026 is the Orion Analytics Dashboard...",
    metadata={"sources": ["knowledge_bot_data.txt"]}
)

# Get conversation history
history = json_storage.get_conversation_history(session_id, limit=10)

# List all sessions
sessions = json_storage.list_sessions(limit=20)

# Export a conversation
export_path = json_storage.export_conversation(session_id)
```

### Configuration

The storage directory can be configured when initializing:

```python
from agent.json_storage import JSONStorage

# Custom storage location
storage = JSONStorage(storage_dir="my_custom_path/conversations")
```

Default location: `data/conversations/`

## 📤 Exporting Conversations

### Export Single Conversation

```python
# Export to default location
json_storage.export_conversation(session_id)

# Export to specific file
json_storage.export_conversation(
    session_id,
    output_file="exports/conversation_2025-12-23.json"
)
```

### Export Format

Exported conversations include:
- Session metadata
- Complete conversation history
- Export timestamp

```json
{
  "session": {
    "session_id": "...",
    "user_id": "...",
    "created_at": "...",
    "message_count": 15
  },
  "conversation": [
    {
      "message_id": "...",
      "role": "user",
      "content": "..."
    }
  ],
  "exported_at": "2025-12-23T20:30:00"
}
```

## 🔍 Viewing Conversations

### Method 1: Direct File Access

Navigate to `data/conversations/conversations/` and open any `.json` file with a text editor or JSON viewer.

### Method 2: Python Script

```python
import json
from pathlib import Path

# Load a conversation
conversation_file = Path("data/conversations/conversations/<session-id>.json")
with open(conversation_file, 'r') as f:
    data = json.load(f)

# Print messages
for msg in data['messages']:
    print(f"{msg['role']}: {msg['content']}\n")
```

### Method 3: CLI Tool (Future Enhancement)

```bash
# List sessions
python cli.py --list-sessions

# View conversation
python cli.py --view-session <session-id>

# Export conversation
python cli.py --export-session <session-id>
```

## 🗑️ Managing Storage

### Delete Old Sessions

```python
# Delete specific session
json_storage.delete_session(session_id)

# Delete old sessions (custom script)
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

sessions_file = Path("data/conversations/sessions.json")
with open(sessions_file, 'r') as f:
    sessions = json.load(f)

cutoff_date = datetime.now() - timedelta(days=30)

for session_id, session_data in list(sessions.items()):
    updated_at = datetime.fromisoformat(session_data['updated_at'])
    if updated_at < cutoff_date:
        json_storage.delete_session(session_id)
        print(f"Deleted old session: {session_id}")
```

### Backup Conversations

```bash
# Simple backup
xcopy "data\conversations" "backups\conversations_%date%" /E /I

# Or on Linux/Mac
cp -r data/conversations backups/conversations_$(date +%Y%m%d)
```

## 🔐 Security & Privacy

### Recommendations

1. **Exclude from Git (if sensitive)**
   ```
   # .gitignore
   data/conversations/
   ```

2. **Encrypt Sensitive Data**
   ```python
   # Example: encrypt before saving
   from cryptography.fernet import Fernet
   
   key = Fernet.generate_key()
   cipher = Fernet(key)
   
   encrypted_content = cipher.encrypt(content.encode())
   ```

3. **Regular Backups**
   - Set up automated backups
   - Store backups securely
   - Test restore procedures

4. **Access Control**
   - Set appropriate file permissions
   - Use user-specific directories for multi-user systems

## 📊 Storage Size Management

### Monitor Storage Size

```python
from pathlib import Path

conversations_dir = Path("data/conversations")
total_size = sum(f.stat().st_size for f in conversations_dir.rglob('*') if f.is_file())

print(f"Total storage: {total_size / 1024 / 1024:.2f} MB")
```

### Archive Old Conversations

```python
import shutil
from datetime import datetime

# Archive conversations older than 90 days
archive_dir = Path("archives") / datetime.now().strftime("%Y-%m")
archive_dir.mkdir(parents=True, exist_ok=True)

# Move old sessions to archive
# (implement based on your retention policy)
```

## 🔄 Migration from PostgreSQL

If you had conversations in PostgreSQL, you can migrate them:

```python
import asyncio
import asyncpg
from agent.json_storage import json_storage

async def migrate_from_postgres():
    conn = await asyncpg.connect("your_database_url")
    
    # Get all sessions
    sessions = await conn.fetch("SELECT * FROM sessions")
    
    for session in sessions:
        # Create JSON session
        session_id = str(session['id'])
        
        # Get messages for this session
        messages = await conn.fetch(
            "SELECT * FROM messages WHERE session_id = $1 ORDER BY created_at",
            session['id']
        )
        
        # Save to JSON
        for msg in messages:
            json_storage.add_message(
                session_id=session_id,
                role=msg['role'],
                content=msg['content'],
                metadata=msg.get('metadata', {})
            )
    
    await conn.close()
    print("Migration complete!")

# Run migration
asyncio.run(migrate_from_postgres())
```

## 🚀 Performance Considerations

### Pros
- **Fast Read/Write** for individual conversations
- **No Database Overhead** for conversation storage
- **Simple Deployment** - no database setup needed

### Cons
- **Search Limitations** - can't easily search across all conversations
- **Concurrent Access** - file locking may be needed for high concurrency
- **Scalability** - may need database for thousands of concurrent users

### When to Consider Database Storage
- More than 1000 active users
- Need to search across all conversations
- Require complex analytics on conversation data
- High concurrency requirements

## 💡 Tips & Best Practices

1. **Periodic Cleanup**
   - Delete sessions older than X days
   - Archive completed conversations

2. **Metadata Usage**
   - Add meaningful metadata to sessions
   - Tag conversations by project/topic
   - Store user preferences

3. **Backup Strategy**
   - Daily automated backups
   - Keep 7 daily + 4 weekly backups
   - Test restore process

4. **Monitoring**
   - Track storage size growth
   - Monitor number of active sessions
   - Log conversation statistics

## 🆘 Troubleshooting

### Issue: "Permission denied" errors
**Solution:** Check file permissions on `data/conversations/` directory

### Issue: Large storage size
**Solution:** Implement cleanup policy, archive old conversations

### Issue: Corrupted JSON files
**Solution:** Validate JSON on write, keep backups, implement recovery

### Issue: Missing conversations
**Solution:** Check backup, verify session_id, check file permissions

## 📝 Summary

JSON-based storage simplifies the conversation management by:
- ✅ No PostgreSQL needed for conversations
- ✅ Easy to view, backup, and manage
- ✅ Simple setup and deployment
- ✅ Human-readable format

Perfect for small to medium deployments where simplicity is preferred over advanced database features.

---

**Note:** Vector search and knowledge graph still require PostgreSQL and Neo4j respectively. This change only affects conversation/session storage.

