"""
JSON-based storage for conversations.
Saves all conversations by user_id only - when user returns, continues from their history.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import uuid
import logging

logger = logging.getLogger(__name__)


class JSONStorage:
    """Manages JSON-based storage for conversations by user_id."""
    
    def __init__(self, storage_dir: str = "transcription"):
        """
        Initialize JSON storage.
        
        Args:
            storage_dir: Directory to store JSON files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.users_dir = self.storage_dir / "users"
        self.users_dir.mkdir(exist_ok=True)
        
        logger.info(f"JSON storage initialized at {self.users_dir}")
    
    def _save_json(self, filepath: Path, data: Any) -> None:
        """Save data to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def _load_json(self, filepath: Path) -> Any:
        """Load data from JSON file."""
        if not filepath.exists():
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_user_file(self, user_id: str) -> Path:
        """Get the file path for a user's conversation history."""
        # Sanitize user_id for filename
        safe_user_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return self.users_dir / f"{safe_user_id}.json"
    
    def _get_or_create_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get existing user data or create new."""
        user_file = self._get_user_file(user_id)
        user_data = self._load_json(user_file)
        
        if not user_data:
            user_data = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "message_count": 0,
                "messages": []
            }
            self._save_json(user_file, user_data)
            logger.info(f"Created new user file for: {user_id}")
        
        return user_data
    
    def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create/get session for user. Returns user_id as session_id.
        
        Args:
            user_id: User identifier (required)
            metadata: Optional metadata
        
        Returns:
            user_id as session identifier
        """
        user_id = user_id or "anonymous"
        
        # Ensure user file exists
        self._get_or_create_user_data(user_id)
        
        logger.info(f"Session ready for user: {user_id}")
        return user_id  # Return user_id as the session identifier
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID (which is now user_id).
        
        Args:
            session_id: Session/User identifier
        
        Returns:
            User data or None
        """
        user_file = self._get_user_file(session_id)
        return self._load_json(user_file)
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to a user's conversation history.
        session_id is actually user_id now.
        
        Args:
            session_id: User identifier (used as session_id for compatibility)
            role: Message role (user/assistant)
            content: Message content
            metadata: Optional message metadata
        
        Returns:
            Message ID
        """
        user_id = session_id  # session_id is now user_id
        message_id = str(uuid.uuid4())
        
        # Get or create user data
        user_data = self._get_or_create_user_data(user_id)
        
        message = {
            "message_id": message_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        user_data["messages"].append(message)
        user_data["updated_at"] = datetime.now().isoformat()
        user_data["message_count"] = len(user_data["messages"])
        
        # Save to user file
        user_file = self._get_user_file(user_id)
        self._save_json(user_file, user_data)
        
        logger.debug(f"Added message {message_id} for user {user_id}")
        return message_id
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a user.
        session_id is actually user_id now.
        
        Args:
            session_id: User identifier
            limit: Maximum number of messages to return
        
        Returns:
            List of messages (most recent)
        """
        user_id = session_id
        user_file = self._get_user_file(user_id)
        user_data = self._load_json(user_file)
        
        if not user_data:
            return []
        
        messages = user_data.get("messages", [])
        return messages[-limit:] if limit else messages
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a user's conversation history.
        session_id is actually user_id now.
        
        Args:
            session_id: User identifier
        
        Returns:
            True if deleted, False otherwise
        """
        user_id = session_id
        user_file = self._get_user_file(user_id)
        
        if user_file.exists():
            user_file.unlink()
            logger.info(f"Deleted conversation history for user: {user_id}")
            return True
        
        return False
    
    def clear_user_history(self, user_id: str) -> bool:
        """
        Clear a user's conversation history but keep the file.
        
        Args:
            user_id: User identifier
        
        Returns:
            True if cleared
        """
        user_file = self._get_user_file(user_id)
        
        if user_file.exists():
            user_data = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "message_count": 0,
                "messages": []
            }
            self._save_json(user_file, user_data)
            logger.info(f"Cleared conversation history for user: {user_id}")
            return True
        
        return False

    def add_feedback(
        self,
        session_id: str,
        message_id: str,
        feedback_type: str,
        comment: Optional[str] = None,
        actor_id: Optional[str] = None
    ) -> bool:
        """
        Add feedback (like/dislike/comment) to a message in the user's conversation history.

        Args:
            session_id: User identifier (session id)
            message_id: ID of the message to attach feedback to
            feedback_type: One of 'like', 'dislike', 'comment'
            comment: Optional textual comment when feedback_type is 'comment'
            actor_id: The user who submitted the feedback (optional)

        Returns:
            True if feedback was saved, False otherwise
        """
        user_file = self._get_user_file(session_id)
        user_data = self._load_json(user_file)

        # If no user data found for the provided session_id, attempt to locate the message
        # across all user files (message IDs are UUIDs and may belong to another session).
        if not user_data:
            logger.warning(f"No user data found for {session_id} - searching all users for message {message_id}")
            # Search all user files for the message_id
            for other_file in self.users_dir.glob("*.json"):
                other_data = self._load_json(other_file)
                if not other_data:
                    continue
                for msg in other_data.get("messages", []):
                    if msg.get("message_id") == message_id:
                        # Found the message in another user's file; attach feedback there
                        feedback = msg.get("feedback", [])
                        entry = {
                            "feedback_type": feedback_type,
                            "comment": comment,
                            "actor_id": actor_id,
                            "timestamp": datetime.now().isoformat()
                        }
                        feedback.append(entry)
                        msg["feedback"] = feedback
                        other_data["updated_at"] = datetime.now().isoformat()
                        self._save_json(other_file, other_data)
                        logger.info(f"Saved feedback for message {message_id} in file {other_file.name}")
                        return True

            logger.warning(f"Attempted to add feedback but no user data found for {session_id} and message not located")
            return False
        
        # Additional fallback: frontend may send ephemeral IDs like 'msg_<timestamp>_xxxx'.
        # Attempt to extract a timestamp from such IDs and match messages by timestamp proximity.
        if str(message_id).startswith('msg_'):
            import re
            m = re.search(r'msg_(\d{10,13})', str(message_id))
            if m:
                try:
                    ts_ms = int(m.group(1))
                    ts = datetime.fromtimestamp(ts_ms / 1000.0)
                    # Search all users for assistant messages within +/- 15 seconds
                    time_window_secs = 15
                    for other_file in self.users_dir.glob('*.json'):
                        other_data = self._load_json(other_file)
                        if not other_data:
                            continue
                        for msg in other_data.get('messages', []):
                            # Only consider assistant messages
                            if msg.get('role') != 'assistant':
                                continue
                            try:
                                msg_ts = datetime.fromisoformat(msg.get('timestamp'))
                            except Exception:
                                continue
                            delta = abs((msg_ts - ts).total_seconds())
                            if delta <= time_window_secs:
                                # Found a close timestamp match; attach feedback
                                feedback = msg.get('feedback', [])
                                entry = {
                                    "feedback_type": feedback_type,
                                    "comment": comment,
                                    "actor_id": actor_id,
                                    "timestamp": datetime.now().isoformat()
                                }
                                feedback.append(entry)
                                msg["feedback"] = feedback
                                other_data["updated_at"] = datetime.now().isoformat()
                                self._save_json(other_file, other_data)
                                logger.info(f"Saved feedback for message {message_id} by timestamp match in file {other_file.name}")
                                return True
                except Exception as e:
                    logger.debug(f"Timestamp-based feedback matching failed: {e}")

        messages = user_data.get("messages", [])
        for msg in messages:
            if msg.get("message_id") == message_id:
                feedback = msg.get("feedback", [])
                entry = {
                    "feedback_type": feedback_type,
                    "comment": comment,
                    "actor_id": actor_id,
                    "timestamp": datetime.now().isoformat()
                }
                feedback.append(entry)
                msg["feedback"] = feedback

                # Update metadata for the user file
                user_data["updated_at"] = datetime.now().isoformat()
                user_data["message_count"] = len(messages)
                self._save_json(user_file, user_data)
                logger.info(f"Saved feedback for message {message_id} (user {session_id})")
                return True

        logger.warning(f"Message id {message_id} not found for user {session_id}")
        return False
    
    def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        List all users with conversations.
        
        Args:
            user_id: If provided, returns only this user's data
            limit: Maximum number of users
        
        Returns:
            List of user session data
        """
        if user_id:
            # Return just this user's data
            user_data = self.get_session(user_id)
            return [user_data] if user_data else []
        
        # List all user files
        user_list = []
        for user_file in self.users_dir.glob("*.json"):
            user_data = self._load_json(user_file)
            if user_data:
                user_list.append({
                    "user_id": user_data.get("user_id"),
                    "message_count": user_data.get("message_count", 0),
                    "created_at": user_data.get("created_at"),
                    "updated_at": user_data.get("updated_at")
                })
        
        # Sort by updated_at descending
        user_list.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return user_list[:limit]
    
    def export_conversation(self, user_id: str, output_file: Optional[str] = None) -> str:
        """
        Export user's conversation to a formatted JSON file.
        
        Args:
            user_id: User identifier
            output_file: Optional output file path
        
        Returns:
            Path to exported file
        """
        if not output_file:
            output_file = f"conversation_export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        user_data = self.get_session(user_id)
        
        export_data = {
            "user_id": user_id,
            "conversation": user_data,
            "exported_at": datetime.now().isoformat()
        }
        
        output_path = Path(output_file)
        self._save_json(output_path, export_data)
        
        logger.info(f"Exported conversation to: {output_path}")
        return str(output_path)


# Global storage instance
json_storage = JSONStorage()


def get_json_storage() -> JSONStorage:
    """Get the global JSON storage instance."""
    return json_storage

