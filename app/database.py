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
    def __init__(self, db_path: str = "storage/metadata.db"):
        self.db_path = db_path
        if self.db_path != ":memory:" and os.path.dirname(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        if self.db_path != ":memory:" and os.path.dirname(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id TEXT PRIMARY KEY,
                    owner_username TEXT DEFAULT 'admin',
                    owner_id TEXT,
                    name TEXT NOT NULL,
                    player1 TEXT NOT NULL,
                    player2 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    video_filename TEXT,
                    original_filename TEXT,
                    events TEXT NOT NULL DEFAULT '[]',
                    renders TEXT NOT NULL DEFAULT '[]',
                    fps REAL,
                    duration REAL,
                    width INTEGER,
                    height INTEGER,
                    rendered_video_filename TEXT
                )
            """)
            existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(matches)").fetchall()]
            for col, col_type in [
                ("fps", "REAL"),
                ("duration", "REAL"),
                ("width", "INTEGER"),
                ("height", "INTEGER"),
                ("rendered_video_filename", "TEXT"),
                ("renders", "TEXT DEFAULT '[]'"),
                ("owner_id", "TEXT")
            ]:
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE matches ADD COLUMN {col} {col_type}")
            conn.commit()

    def create_match(self, match_data: dict) -> dict:
        events = match_data.get("events", [])
        renders = match_data.get("renders", [])
        
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO matches (
                    id, owner_username, owner_id, name, player1, player2, created_at,
                    video_filename, original_filename, events, renders,
                    fps, duration, width, height, rendered_video_filename
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match_data["id"],
                    match_data.get("owner_username", "admin"),
                    match_data.get("owner_id"),
                    match_data["name"],
                    match_data["player1"],
                    match_data["player2"],
                    match_data.get("created_at", datetime.utcnow().isoformat()),
                    match_data.get("video_filename"),
                    match_data.get("original_filename"),
                    json.dumps(events),
                    json.dumps(renders),
                    match_data.get("fps"),
                    match_data.get("duration"),
                    match_data.get("width"),
                    match_data.get("height"),
                    match_data.get("rendered_video_filename")
                )
            )
            conn.commit()
        return self.get_match(match_data["id"])

    def get_match(self, match_id: str) -> dict:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
            if row:
                res = dict(row)
                res["events"] = json.loads(res.get("events") or "[]")
                res["renders"] = json.loads(res.get("renders") or "[]")
                return res
        return None

    def list_matches(self) -> list[dict]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM matches ORDER BY created_at DESC").fetchall()
            matches = []
            for row in rows:
                m = dict(row)
                m["events"] = json.loads(m.get("events") or "[]")
                m["renders"] = json.loads(m.get("renders") or "[]")
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


from decimal import Decimal

def _to_dynamo_item(val):
    """Recursively converts Python float types to Decimal for boto3 DynamoDB."""
    if isinstance(val, float):
        return Decimal(str(val))
    elif isinstance(val, dict):
        return {k: _to_dynamo_item(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [_to_dynamo_item(v) for v in val]
    return val

def _from_dynamo_item(val):
    """Recursively converts Decimal types back to floats/ints for JSON serialization."""
    if isinstance(val, Decimal):
        if val % 1 == 0:
            return int(val)
        return float(val)
    elif isinstance(val, dict):
        return {k: _from_dynamo_item(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [_from_dynamo_item(v) for v in val]
    return val


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
            "original_filename": match_data.get("original_filename", ""),
            "owner_username": match_data.get("owner_username", "admin"),
            "owner_id": match_data.get("owner_id"),
            "events": match_data.get("events", []),
            "renders": match_data.get("renders", [])
        }
        for attr in ("fps", "duration", "width", "height", "rendered_video_filename"):
            if attr in match_data and match_data[attr] is not None:
                item[attr] = match_data[attr]

        dynamo_item = _to_dynamo_item(item)
        self.table.put_item(Item=dynamo_item)
        return _from_dynamo_item(dynamo_item)

    def get_match(self, match_id: str) -> dict:
        response = self.table.get_item(Key={"id": match_id})
        item = response.get("Item")
        return _from_dynamo_item(item) if item else None

    def list_matches(self) -> list[dict]:
        items = []
        response = self.table.scan()
        items.extend(response.get("Items", []))
        
        while "LastEvaluatedKey" in response:
            response = self.table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
            
        items = [_from_dynamo_item(i) for i in items]
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def update_match_events(self, match_id: str, events: list) -> dict:
        dynamo_events = _to_dynamo_item(events)
        response = self.table.update_item(
            Key={"id": match_id},
            UpdateExpression="set events = :e",
            ExpressionAttributeValues={":e": dynamo_events},
            ReturnValues="ALL_NEW"
        )
        return _from_dynamo_item(response.get("Attributes"))

    def delete_match(self, match_id: str) -> bool:
        try:
            self.table.delete_item(Key={"id": match_id})
            return True
        except Exception:
            return False


def get_db_repository() -> DatabaseRepository:
    """
    Factory function returning the active Database Repository.
    If DB_TYPE=sqlite or local is explicitly set, uses SQLite.
    Otherwise (for production, S3 mode, or cloud deployments), defaults to AWS DynamoDB
    so match records persist permanently across deployments.
    """
    db_type = os.getenv("DB_TYPE", "").lower()
    storage_type = os.getenv("STORAGE_TYPE", "local").lower()
    
    # If explicitly requested sqlite/local or running local mode without DB_TYPE override
    if db_type in ("sqlite", "local") or (not db_type and storage_type == "local"):
        db_path = os.getenv("SQLITE_DB_PATH", os.path.join("storage", "metadata.db"))
        return SQLiteRepository(db_path=db_path)
    
    # Default to DynamoDB for cloud/production/S3 deployments
    table_name = os.getenv("DYNAMODB_TABLE_NAME", "tt_video_editor_matches")
    return DynamoDBRepository(table_name=table_name)
