from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import mysql.connector


@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


class DatabaseConnection:
    """Singleton-like DB connection factory.

    Note: We create short-lived connections per operation (safe for simple Flask apps).
    """

    _instance: Optional["DatabaseConnection"] = None

    def __init__(self, config: DBConfig):
        self._config = config

    @classmethod
    def get_instance(cls, config: DBConfig) -> "DatabaseConnection":
        if cls._instance is None:
            cls._instance = DatabaseConnection(config)
        return cls._instance

    def connect(self):
        return mysql.connector.connect(
            host=self._config.host,
            port=int(self._config.port),
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
        )
