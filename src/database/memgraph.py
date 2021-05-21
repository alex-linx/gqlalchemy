import os
from typing import Any, Dict, List, Iterator, Optional, Union
from .database.connection import Connection
from .database.models import (
    MemgraphConstraint,
    MemgraphConstraintExists,
    MemgraphConstraintUnique,
    MemgraphIndex,
)

__all__ = ("Memgraph",)


MG_HOST = os.getenv("MG_HOST", "127.0.0.1")
MG_PORT = int(os.getenv("MG_PORT", "7687"))
MG_USERNAME = os.getenv("MG_USERNAME", "")
MG_PASSWORD = os.getenv("MG_PASSWORD", "")
MG_ENCRYPTED = os.getenv("MG_ENCRYPT", "false").lower() == "true"


class MemgraphConstants:
    LABEL = "label"
    PROPERTY = "property"
    PROPERTIES = "properties"


class Memgraph:
    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = "",
        password: str = "",
        encrypted: bool = None,
    ):
        self._host = host or MG_HOST
        self._port = port or MG_PORT
        self._username = username or MG_USERNAME
        self._password = password or MG_PASSWORD
        self._encrypted = encrypted if encrypted is not None else MG_ENCRYPTED
        self._cached_connection: Optional[Connection] = None

    def execute_and_fetch(self, query: str, connection: Connection = None) -> Iterator[Dict[str, Any]]:
        """Executes Cypher query and returns iterator of results."""
        connection = connection or self._get_cached_connection()
        return connection.execute_and_fetch(query)

    def execute_query(self, query: str, connection: Connection = None) -> None:
        """Executes Cypher query without returning any results."""
        connection = connection or self._get_cached_connection()
        return connection.execute_query(query)

    def create_index(self, index: MemgraphIndex) -> None:
        """Creates an index (label or label-property type) in the database"""
        query = f"CREATE INDEX ON {index.to_cypher()}"
        self.execute_query(query)

    def drop_index(self, index: MemgraphIndex) -> None:
        """Drops an index (label or label-property type) in the database"""
        query = f"DROP INDEX ON {index.to_cypher()}"
        self.execute_query(query)

    def get_indexes(self) -> List[MemgraphIndex]:
        """Returns a list of all database indexes (label and label-property types)"""
        indexes = []
        for result in self.execute_and_fetch("SHOW INDEX INFO"):
            indexes.append(MemgraphIndex(result[MemgraphConstants.LABEL], result[MemgraphConstants.PROPERTY]))
        return indexes

    def ensure_indexes(self, indexes: List[MemgraphIndex]) -> None:
        """Ensures that database indexes match input indexes"""
        old_indexes = set(self.get_indexes())
        new_indexes = set(indexes)
        for obsolete_index in old_indexes.difference(new_indexes):
            self.drop_index(obsolete_index)
        for missing_index in new_indexes.difference(old_indexes):
            self.create_index(missing_index)

    def create_constraint(self, index: MemgraphConstraint) -> None:
        """Creates a constraint (label or label-property type) in the database"""
        query = f"CREATE CONSTRAINT ON {index.to_cypher()}"
        self.execute_query(query)

    def drop_constraint(self, index: MemgraphConstraint) -> None:
        """Drops a constraint (label or label-property type) in the database"""
        query = f"DROP CONSTRAINT ON {index.to_cypher()}"
        self.execute_query(query)

    def get_constraints(self) -> List[Union[MemgraphConstraintExists, MemgraphConstraintUnique]]:
        """Returns a list of all database constraints (label and label-property types)"""
        indexes: List[Union[MemgraphConstraintExists, MemgraphConstraintUnique]] = []
        for result in self.execute_and_fetch("SHOW CONSTRAINT INFO"):
            if result["constraint type"] == "unique":
                indexes.append(
                    MemgraphConstraintUnique(result[MemgraphConstants.LABEL], result[MemgraphConstants.PROPERTIES])
                )
            elif result["constraint type"] == "exists":
                indexes.append(
                    MemgraphConstraintExists(result[MemgraphConstants.LABEL], result[MemgraphConstants.PROPERTIES])
                )
        return indexes

    def drop_database(self):
        """Drops database by removing all nodes and edges"""
        self.execute_query("MATCH (n) DETACH DELETE n")

    def _get_cached_connection(self) -> Connection:
        """Returns cached connection if it exists, creates it otherwise"""
        if self._cached_connection is None or not self._cached_connection.is_active():
            self._cached_connection = self.new_connection()

        return self._cached_connection

    def new_connection(self) -> Connection:
        """Creates new Memgraph connection"""
        args = dict(
            host=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            encrypted=self._encrypted,
        )
        return Connection.create(**args)
