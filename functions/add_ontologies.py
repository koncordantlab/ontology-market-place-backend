from flask import Flask, Request, jsonify, request as flask_request
from typing import List, Optional
from pydantic import ValidationError
from .model_ontology import NewOntology, Ontology, OntologyResponse
from datetime import datetime, timezone
from .n4j import get_neo4j_driver
from .auth_utils import firebase_auth_required, get_authenticated_email, get_auth_headers_and_email
from functools import wraps
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a Flask app instance
app = Flask(__name__)

# Enable CORS for all routes
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS, GET'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

def add_ontologies(
    ontology_data: list[dict],
    created_time_override: datetime = None,
    email: str = None,
    request: Optional[Request] = None,
) -> OntologyResponse:
    """
    Add new ontologies to the database.
    
    Args:
        ontology_data: List of dictionaries containing ontology data
        created_time_override: Optional datetime to use for all created_time fields.
                              If None, current time will be used.
        email: String email of the owner of ontologies (deprecated, will be obtained from auth)
        request: Optional Flask request object for authentication
        
    Returns:
        Tuple of (response_data, status_code, headers)
        
    Note:
        The email parameter is deprecated and will be obtained from the authentication token.
        For backward compatibility, if email is provided directly, it will be used.
    """
    # Get authentication headers and verify user
    auth_result = get_auth_headers_and_email(request, email)
    if len(auth_result) == 2:  # Success case: (headers, email)
        headers, email = auth_result
    else:  # Error case: (error_response, status_code, headers)
        return auth_result

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
            // Merge the User node
            MERGE (u:User {email: $email})
            // Create the Ontology node and relationship
            MERGE (o:Ontology {uid: onto.uid})
            ON CREATE SET 
                o.title = onto.title,
                o.file_url = onto.file_url,
                o.description = onto.description,
                o.node_count = onto.node_count,
                o.relationship_count = onto.relationship_count,
                o.is_public = onto.is_public,
                o.created_time = datetime(onto.created_time)
            // Create the relationship if it doesn't exist
            MERGE (u)-[:CREATED]->(o)
            RETURN o.uid as uid, o.title as title, u.email as owner_email
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
                    email=email,
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

@app.route('/add_ontologies', methods=['POST', 'OPTIONS'])
@firebase_auth_required
def add_ontologies_endpoint():
    """
    HTTP Cloud Function for adding ontologies.
    """
    if flask_request.method == 'OPTIONS':
        return '', 204

    try:
        # Get JSON data from request
        request_data = flask_request.get_json(silent=True)
        if not request_data or not isinstance(request_data, list):
            return jsonify({
                'success': False,
                'error': 'Request body must be a JSON array of ontology objects'
            }), 400

        # Call the main function with the request object
        result = add_ontologies(
            ontology_data=request_data,
            request=flask_request
        )
        
        # Convert OntologyResponse to JSON response
        if isinstance(result, OntologyResponse):
            return jsonify(result.dict()), 200
        return jsonify(result[0]), result[1]

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        error_response = {
            'success': False,
            'error': 'An unexpected error occurred',
            'details': str(e)
        }
        return jsonify(error_response), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({'status': 'healthy'}), 200

# This is needed for local development
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)