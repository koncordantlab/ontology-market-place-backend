from functions_framework import http
from flask import Request
from typing import List
import json
from pydantic import ValidationError
from .model_ontology import NewOntology, Ontology, OntologyResponse
from datetime import datetime, timezone
from .n4j import get_neo4j_driver

def add_ontologies(
    ontology_data: list[dict], 
    created_time_override: datetime = None
) -> OntologyResponse:
    """
    Add new ontologies to the database.
    
    Args:
        ontology_data: List of dictionaries containing ontology data
        created_time_override: Optional datetime to use for all created_time fields.
                              If None, current time will be used.
        
    Returns:
        Tuple of (response_data, status_code, headers)
    """
    # Set CORS response headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }

    try:
        # Convert and validate input data
        ontologies = Ontology.from_new_ontologies(ontology_data)
        
        # Apply created_time override if provided
        current_time = created_time_override or datetime.now(timezone.utc)
        for onto in ontologies:
            if created_time_override is not None:
                onto.created_time = created_time_override
            else:
                onto.created_time = current_time
        
        
        # Prepare and execute the query
        query = """
            UNWIND $ontologies AS onto
            // First check if an ontology with this file_url already exists
            OPTIONAL MATCH (existing:Ontology {file_url: onto.file_url})
            WITH onto, existing
            // Only proceed if no existing ontology with this file_url was found
            WHERE existing IS NULL
            MERGE (o:Ontology {uid: onto.uid})
            ON CREATE SET 
                o.title = onto.title,
                o.file_url = onto.file_url,
                o.description = onto.description,
                o.node_count = onto.node_count,
                o.relationship_count = onto.relationship_count,
                o.is_public = onto.is_public,
                o.created_time = datetime(onto.created_time)
            RETURN o.uid as uid, o.title as title
        """
        
        # Convert ontologies to dict and serialize datetime
        onto_dicts = [onto.model_dump() for onto in ontologies]
        for onto in onto_dicts:
            if 'created_time' in onto and onto['created_time']:
                onto['created_time'] = onto['created_time'].isoformat()
        
        # Execute the query 
        try:
            with get_neo4j_driver() as driver:
                result = driver.execute_query(
                    query,
                    ontologies=onto_dicts,
                    database_="neo4j",
                    result_transformer_=lambda r: [dict(record) for record in r]
                )
        
                print(f'Ontologies added: {result}')
                    
                # Prepare success response
                response_data = {
                    'success': True,
                    'message': f'Successfully added {len(result)} ontologies. Skipped {len(ontologies) - len(result)} ontologies that already existed.',
                    'data': {
                        'created_ontologies': [{'uid': r['uid'], 'title': r['title']} for r in result]
                            }
                        }
        
                return OntologyResponse(**response_data)
                        
        except Exception as e:
            print(f"Database error: {str(e)}")
            return OntologyResponse(
                success=False,
                message='Database operation failed',
                data=None
            )

    except ValidationError as e:
        return OntologyResponse(
            success=False,
            message='Validation error',
            data=None
        )
    except Exception as e:
        print(f"Error adding ontologies: {str(e)}")
        return OntologyResponse(
            success=False,
            message='Failed to add ontologies',
            data=None
        )

# Entry point for Google Cloud Run
@http
def add_ontologies_by_request(request: Request):
    """
    HTTP Cloud Function for adding ontologies.
    Args:
        request (flask.Request): The request object.
        Should contain a JSON array of ontology objects.
    Returns:
        JSON response with the result of the operation.
    """
    # Set CORS headers for the preflight request
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
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
            return ('No JSON data provided', 400, headers)

        return add_ontologies(request_json)

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return OntologyResponse(
            success=False,
            message='An unexpected error occurred',
            data=None
        )