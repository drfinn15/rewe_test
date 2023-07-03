import sqlite3
from typing import Dict, Optional
from dataclasses import dataclass


import httpx

from viktualien.config import Config

# Modul zum Caching von HTTP-Abfragen und Antworten
# Nutzt intern eine SQLite-Datenbank im Config-Verzeichnis

def _ensure_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS http_cache (
            url TEXT PRIMARY KEY,
            status INT NOT NULL,
            response TEXT,
            time INT NOT NULL
        ) STRICT
    """
    )
    cur.close()


def _open_cache() -> sqlite3.Connection:
    path = Config.get().cache_path()
    return sqlite3.connect(path, isolation_level=None)


@dataclass(frozen=True)
class HTTPError(Exception):
    status: int


def get(
    uri: str,
    params: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    logger = Config.get().logger("cached_http")

    with _open_cache() as conn:
        request = httpx.Request("GET", uri, params=params, headers=headers)
        request.headers["User-Agent"] = "Wolpertinger/42"

        request_url = str(request.url)
        logger.info("Requesting %s ...", request_url)

        _ensure_table(conn)
        cur = conn.cursor()

        cur.execute(
            "SELECT status, response FROM http_cache WHERE url = ?", (request_url,)
        )
        row = cur.fetchone()

        if row:
            logger.info("Cache hit")

            status = int(row[0])
            if status == 200:
                return row[1]

            raise HTTPError(status)

        logger.info("Cache miss")

        with httpx.Client() as client:
            response = client.send(request)
            text = response.text if response.status_code == 200 else None

            if response.status_code in (200, 404):
                cur.execute(
                    "INSERT INTO http_cache VALUES (?, ?, ?, strftime('%s'))",
                    (request_url, response.status_code, text),
                )
            else:
                logger.warn(f"Unexpected status code {response.status_code}")

            if response.status_code == 200:
                return response.text

            raise HTTPError(response.status_code)
