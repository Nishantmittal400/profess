import sqlite3, json, time, hashlib, os
from typing import Any, Dict, Tuple, Optional

class SQLiteCache:
    def __init__(self, path: Optional[str]):
        self.path = path
        self.disabled = not path
        if self.disabled:
            return
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)
        with sqlite3.connect(self.path) as c:
            self._ensure_schema(c)

    @staticmethod
    def _hash(payload: Dict[str, Any]) -> str:
        s = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
              k TEXT PRIMARY KEY,
              v TEXT,
              created REAL,
              meta TEXT
            )
            """
        )

    def get_or_set(self, payload: Dict[str, Any], fn) -> Tuple[dict, dict]:
        if self.disabled:
            return fn()
        key = self._hash(payload)
        with sqlite3.connect(self.path) as c:
            self._ensure_schema(c)
            row = c.execute("SELECT v, meta FROM cache WHERE k=?", (key,)).fetchone()
            if row:
                return json.loads(row[0]), (json.loads(row[1]) if row[1] else {})
            val, meta = fn()
            c.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?,?)",
                      (key, json.dumps(val, ensure_ascii=False), time.time(), json.dumps(meta)))
            c.commit()
            return val, meta
