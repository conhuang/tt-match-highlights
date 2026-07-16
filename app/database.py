import os
import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime

class DatabaseRepository(ABC):
    """
    Abstract Base Class for the Database Repository Pattern.
    Defines database operations for match records.
    """
    @abstractmethod
    def create_match(self, match_data: dict) -> dict:
        pass

    @abstractmethod
    def get_match(self, match_id: str) -> dict:
        pass

    @abstractmethod
    def list_matches(self) -> list[dict]:
        pass

    @abstractmethod
    def update_match_events(self, match_id: str, events: list) -> dict:
        pass

    @abstractmethod
    def delete_match(self, match_id: str) -> bool:
        pass


class SQLiteRepository(DatabaseRepository):
    """
    SQLite implementation of DatabaseRepository.
    Ideal for local development and fast testing.
    """
    def __init__(self, db_path: str = "metadata.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id TEXT PRIMARY KEY,
                    owner_username TEXT DEFAULT 'admin',
                    name TEXT NOT NULL,
                    player1 TEXT NOT NULL,
                    player2 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    video_filename TEXT,
                    original_filename TEXT,
                    events TEXT NOT NULL DEFAULT '[]'
                )
            """)
            conn.commit()

    def create_match(self, match_data: dict) -> dict:
        events = match_data.get("events", [])
        
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO matches (id, owner_username, name, player1, player2, created_at, video_filename, original_filename, events)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match_data["id"],
                    match_data.get("owner_username", "admin"),
                    match_data["name"],
                    match_data["player1"],
                    match_data["player2"],
                    match_data.get("created_at", datetime.utcnow().isoformat()),
                    match_data.get("video_filename"),
                    match_data.get("original_filename"),
                    json.dumps(events)
                )
            )
            conn.commit()
        return self.get_match(match_data["id"])

    def get_match(self, match_id: str) -> dict:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
            if row:
                res = dict(row)
                res["events"] = json.loads(res["events"])
                return res
        return None

    def list_matches(self) -> list[dict]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM matches ORDER BY created_at DESC").fetchall()
            matches = []
            for row in rows:
                m = dict(row)
                m["events"] = json.loads(m["events"])
                matches.append(m)
            return matches

    def update_match_events(self, match_id: str, events: list) -> dict:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE matches SET events = ? WHERE id = ?",
                (json.dumps(events), match_id)
            )
            conn.commit()
        return self.get_match(match_id)

    def delete_match(self, match_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM matches WHERE id = ?", (match_id,))
            conn.commit()
            return cursor.rowcount > 0


class DynamoDBRepository(DatabaseRepository):
    """
    AWS DynamoDB implementation of DatabaseRepository.
    Ideal for cloud serverless deployments.
    """
    def __init__(self, table_name: str = "tt_video_editor_matches"):
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for DynamoDB. Please install it using 'pip install boto3'"
            )
        
        self.dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-2"))
        self.table = self.dynamodb.Table(table_name)

    def create_match(self, match_data: dict) -> dict:
        item = {
            "id": match_data["id"],
            "name": match_data["name"],
            "player1": match_data["player1"],
            "player2": match_data["player2"],
            "created_at": match_data.get("created_at", datetime.utcnow().isoformat()),
            "video_filename": match_data.get("video_filename", ""),
            "events": match_data.get("events", [])
        }
        self.table.put_item(Item=item)
        return item

    def get_match(self, match_id: str) -> dict:
        response = self.table.get_item(Key={"id": match_id})
        return response.get("Item")

    def list_matches(self) -> list[dict]:
        response = self.table.scan()
        items = response.get("Items", [])
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def update_match_events(self, match_id: str, events: list) -> dict:
        response = self.table.update_item(
            Key={"id": match_id},
            UpdateExpression="set events = :e",
            ExpressionAttributeValues={":e": events},
            ReturnValues="ALL_NEW"
        )
        return response.get("Attributes")

    def delete_match(self, match_id: str) -> bool:
        try:
            self.table.delete_item(Key={"id": match_id})
            return True
        except Exception:
            return False


def get_db_repository() -> DatabaseRepository:
    """
    Factory function returning the active Database Repository.
    Reads DB_TYPE environment variable (defaults to 'sqlite').
    """
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "dynamodb":
        table_name = os.getenv("DYNAMODB_TABLE_NAME", "tt_video_editor_matches")
        return DynamoDBRepository(table_name=table_name)
    else:
        db_path = os.getenv("SQLITE_DB_PATH", "metadata.db")
        return SQLiteRepository(db_path=db_path)
