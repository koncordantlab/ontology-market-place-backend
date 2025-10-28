from typing import List

from .n4j import get_neo4j_driver


def get_tags(neo4j_database: str | None = None) -> List[str]:
    """Return all tag names in lowercase as a list of strings."""
    with get_neo4j_driver().session(database=neo4j_database) as session:
        result = session.run(
            """
            MATCH (t:Tag)
            WITH toLower(t.name) AS name
            RETURN DISTINCT name AS name
            ORDER BY name
            """
        )
        return [record["name"] for record in result]


def add_tags(tags: List[str], neo4j_database: str | None = None) -> List[str]:
    """Create Tag nodes for the provided tag strings, enforcing lowercase and uniqueness.

    Returns the set of all tags that exist after creation, in lowercase.
    """
    if not tags:
        return []

    lowered = [t.strip().lower() for t in tags if isinstance(t, str) and t.strip()]
    if not lowered:
        return []

    with get_neo4j_driver().session(database=neo4j_database) as session:
        # MERGE create tags (idempotent). Use UNWIND batching.
        session.run(
            """
            UNWIND $names AS name
            MERGE (:Tag {name: name})
            """,
            names=lowered,
        )
        # Return all tag names (distinct), lowercased and ordered
        result = session.run(
            """
            MATCH (t:Tag)
            WITH toLower(t.name) AS name
            RETURN DISTINCT name AS name
            ORDER BY name
            """
        )
        return [record["name"] for record in result]
