from typing import Tuple, Optional
from urllib.parse import urlparse
import tempfile
import os

from neo4j import Driver, GraphDatabase
import rdflib
import requests

from .n4j import get_neo4j_driver


def _download_to_tempfile(source: str) -> str:
    """
    Download a remote file to a temporary path and return the path.
    If source is a local path, return it unchanged.
    """
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        response = requests.get(source, timeout=60)
        response.raise_for_status()
        suffix = os.path.splitext(parsed.path)[1] or ".ttl"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(response.content)
        return tmp_path
    return source


def _ensure_indexes(driver: Driver, database: Optional[str] = None) -> None:
    """
    Create minimal indexes/constraints used by the ingest. Idempotent.
    """
    statements = [
        # Resource nodes indexed by uri for faster MERGE
        "CREATE INDEX resource_uri IF NOT EXISTS FOR (n:Resource) ON (n.uri)",
        # Ontology node index by uuid (if used for tracking)
        "CREATE INDEX ontology_uuid IF NOT EXISTS FOR (o:Ontology) ON (o.uuid)",
    ]
    with driver.session(database=database) as session:
        for stmt in statements:
            session.run(stmt)


def _ingest_graph(driver: Driver, graph: rdflib.Graph, database: Optional[str] = None) -> Tuple[int, int]:
    """
    Ingest an RDFLib graph into Neo4j.
    - Creates/merges `Resource {uri}` nodes for subjects/objects that are URIs
    - For object triples (object is URI): creates relationships with `type` equal to predicate IRI
    - For literal triples: sets a property on the subject node keyed by a safe property name derived from predicate

    Returns tuple: (num_nodes_touched, num_relationships_created)
    """
    # We'll batch relationships by predicate to reduce query churn
    object_triples_by_pred = {}
    literal_triples_by_pred = {}

    for subj, pred, obj in graph:
        subj_str = str(subj)
        pred_str = str(pred)
        if isinstance(obj, rdflib.term.URIRef):
            obj_str = str(obj)
            object_triples_by_pred.setdefault(pred_str, []).append((subj_str, obj_str))
        else:
            # Literal property; store value as string for now
            literal_triples_by_pred.setdefault(pred_str, []).append((subj_str, str(obj)))

    total_nodes = 0
    total_rels = 0

    with driver.session(database=database) as session:
        # Ensure base indexes
        _ensure_indexes(driver, database)

        # Upsert subjects/objects for object triples in batches per predicate
        for pred_iri, pairs in object_triples_by_pred.items():
            # Use UNWIND for batching
            cypher = (
                "UNWIND $rows AS row "
                "MERGE (s:Resource {uri: row.subj}) "
                "MERGE (o:Resource {uri: row.obj}) "
                "MERGE (s)-[r:RELATION {type: $pred}]->(o) "
                "RETURN count(distinct s)+count(distinct o) as nodes, count(r) as rels"
            )
            result = session.run(cypher, rows=[{"subj": s, "obj": o} for s, o in pairs], pred=pred_iri)
            record = result.single()
            if record:
                total_nodes += record["nodes"]
                total_rels += record["rels"]

        # Handle literal properties: set properties on subject nodes
        for pred_iri, pairs in literal_triples_by_pred.items():
            # Create a safe property key from predicate IRI
            # Keep a short, consistent property name; fallback to full IRI hashed if needed
            key = _predicate_to_property_key(pred_iri)
            cypher = (
                "UNWIND $rows AS row "
                "MERGE (s:Resource {uri: row.subj}) "
                "SET s[$key] = row.val "
                "RETURN count(distinct s) as nodes"
            )
            result = session.run(cypher, rows=[{"subj": s, "val": v} for s, v in pairs], key=key)
            record = result.single()
            if record:
                total_nodes += record["nodes"]

    return total_nodes, total_rels


def _predicate_to_property_key(predicate_iri: str) -> str:
    """
    Convert a predicate IRI into a safe Neo4j property key.
    Strategy: use fragment or last path segment, with non-alphanumerics replaced by underscores.
    """
    frag = predicate_iri.rsplit("#", 1)[-1]
    frag = frag.rsplit("/", 1)[-1]
    safe = []
    for ch in frag:
        if ch.isalnum():
            safe.append(ch)
        else:
            safe.append("_")
    candidate = "".join(safe)
    # Ensure it starts with a letter per best practice
    if candidate and candidate[0].isdigit():
        candidate = f"p_{candidate}"
    return candidate or "prop"


def _update_ontology_counts(driver: Driver, ontology_uuid: str, nodes: int, rels: int, database: Optional[str] = None) -> None:
    """Update counts on an existing Ontology node by uuid."""
    with driver.session(database=database) as session:
        session.run(
            """
            MATCH (o:Ontology {uuid: $uuid})
            SET o.node_count = $nodes,
                o.relationship_count = $rels,
                o.updated_time = datetime()
            RETURN o
            """,
            uuid=ontology_uuid,
            nodes=int(nodes),
            rels=int(rels),
        )


def upload_ontology(
    source: str,
    ontology_uuid: Optional[str] = None,
    neo4j_uri: Optional[str] = None,
    neo4j_username: Optional[str] = None,
    neo4j_password: Optional[str] = None,
    neo4j_database: Optional[str] = None,
) -> dict:
    """
    Load a TTL file from a URL or local path into Neo4j, similar to the referenced Cloud Function.

    Args:
        source: HTTP(S) URL or filesystem path to a TTL file.
        ontology_uuid: Optional Ontology uuid to update counts on after ingest.

    Returns:
        Dict with counts: {"nodes": int, "relationships": int}
    """
    local_path: Optional[str] = None
    try:
        local_path = _download_to_tempfile(source)
        graph = rdflib.Graph()
        graph.parse(local_path, format="turtle")

        # Choose connection: explicit parameters override env-configured driver
        if neo4j_uri and neo4j_username and neo4j_password:
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
            manage_driver = True
        else:
            driver = get_neo4j_driver()
            manage_driver = True

        try:
            nodes, rels = _ingest_graph(driver, graph, database=neo4j_database)
            if ontology_uuid:
                _update_ontology_counts(driver, ontology_uuid, nodes, rels, database=neo4j_database)
        finally:
            # Close explicit driver or env driver context
            try:
                driver.close()
            except Exception:
                pass

        return {"nodes": int(nodes), "relationships": int(rels)}
    finally:
        # Clean up temp file if we downloaded it
        if local_path and local_path != source and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                pass
