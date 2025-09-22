from functions_framework import http
from flask import Request
from typing import List
from .model_ontology import OntologyResponse
from .n4j import get_neo4j_driver

def delete_ontologies(email: str, ontology_ids: List[str]) -> OntologyResponse:
    """
    Delete ontologies from the database.
    
    Args:
        email: String email of the owner/admin/editor of ontologies
        ontology_ids: List of ontology uuids to delete
        
    Returns:
        OntologyResponse with the result of the operation
    """
    if not ontology_ids:
        return OntologyResponse(
            success=False,
            message="No ontology IDs provided",
            data=None
        )
    
    try:
        driver = get_neo4j_driver()
        
        # Delete ontologies and their relationships
        query = """
            UNWIND $ontology_ids AS ontology_id
            MATCH (o:Ontology {uuid: ontology_id})
            MATCH (u:User {email: $email})
            WHERE EXISTS((u)-[:CREATED|CAN_ADMIN|CAN_EDIT]->(o))
            WITH o, u
            DETACH DELETE o
            RETURN count(o) as deleted_count
        """
        
        result = driver.execute_query(
            query,
            email=email,
            ontology_ids=ontology_ids,
            result_transformer_=lambda r: r.single()["deleted_count"]
        )
        
        if result == 0:
            return OntologyResponse(
                success=False,
                message="No ontologies found with the provided IDs for the given user",
                data={"deleted_count": 0}
            )
        
        return OntologyResponse(
            success=True,
            message=f"Successfully deleted {result} ontologies",
            data={"deleted_count": result}
        )
            
    except Exception as e:
        print(f"Database error: {str(e)}")
        return OntologyResponse(
            success=False,
            message="Failed to delete ontologies",
            data=None
        )

@http
def delete_ontologies_by_request(request: Request):
    """
    HTTP Cloud Function for deleting ontologies.
    
    Args:
        request (flask.Request): The request object.
        Should contain a JSON array of ontology IDs to delete.
        
    Returns:
        JSON response with the result of the operation.
    """
    # Set CORS headers for the preflight request
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }

    try:
        # Get JSON data from request
        request_json = request.get_json(silent=True)
        if not request_json:
            return OntologyResponse(
                success=False,
                message="No JSON data provided",
                data=None
            )
        
        # Extract ontology_ids from request
        if not isinstance(request_json, list):
            return OntologyResponse(
                success=False,
                message="Expected an array of ontology IDs",
                data=None
            )
            
        return delete_ontologies(request_json)

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return OntologyResponse(
            success=False,
            message="An unexpected error occurred",
            data=None
        )