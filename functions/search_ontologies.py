from functions_framework import http
from flask import Request
import json
from typing import Optional
from .model_ontology import Ontology, OntologyResponse
from datetime import datetime
from .n4j import get_neo4j_driver


def search_ontologies(search_term: str = None, limit: int = 100, offset: int = 0) -> OntologyResponse:
    """
    Search for ontologies in the database.
    
    Args:
        search_term: Optional term to search in title and description
        limit: Maximum number of results to return (default: 100, max: 100)
        offset: Number of results to skip for pagination (default: 0)
        
    Returns:
        Tuple of (response_data, status_code, headers)
    """
    # Set CORS response headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }

    # Validate pagination parameters
    limit = min(max(1, limit), 100)  # Ensure limit is between 1 and 100
    offset = max(0, offset)  # Ensure offset is not negative

    try:
        with get_neo4j_driver() as driver:

            # Construct base query
            if search_term:
                query = """
                MATCH (o:Ontology)
                WHERE o.title CONTAINS $search_term 
                OR o.description CONTAINS $search_term
                RETURN o
                ORDER BY o.created_time DESC
                SKIP $offset
                LIMIT $limit
                """
                params = {
                    'search_term': search_term,
                    'offset': offset,
                    'limit': limit
                }
            else:
                query = """
                MATCH (o:Ontology)
                RETURN o
                ORDER BY o.created_time DESC
                SKIP $offset
                LIMIT $limit
                """
                params = {
                    'offset': offset,
                    'limit': limit
                }

            # Execute query and process results
            records = driver.execute_query(
                query,
                params,
                result_transformer_=lambda r: [record['o'] for record in r]
            )

            # Process results
            ontologies = []
            for node in records:
                try:
                    ontology = Ontology(
                        uid=node['uid'],
                        title=node['title'],
                        file_url=node['file_url'],
                        description=node.get('description'),
                        node_count=node.get('node_count'),
                        relationship_count=node.get('relationship_count'),
                        is_public=node.get('is_public', False),
                        created_time=node.get('created_time').to_native()
                    )
                    ontologies.append(ontology)
                except Exception as e:
                    print(f"Error processing ontology record: {e}")
                    continue

            # Get total count for pagination
            count_query = """
            MATCH (o:Ontology)
            WHERE $search_term IS NULL 
            OR o.title CONTAINS $search_term 
            OR o.description CONTAINS $search_term
            RETURN count(o) as total
            """
            count_result = driver.execute_query(
                count_query,
                {'search_term': search_term},
                result_transformer_=lambda r: r.single()['total']
            )

            response_data = {
                'success': True,
                'message': 'Ontologies retrieved successfully',
                'data': {
                    'results': [onto.dict() for onto in ontologies],
                    'count': len(ontologies),
'total': count_result if count_result else 0,
                    'offset': offset,
                    'limit': limit
                }
            }

            return OntologyResponse(**response_data)

    except Exception as e:
        print(f"Database error: {str(e)}")
        return OntologyResponse(
            success=False,
            message='Database error occurred',
            data=None
        )


# Entry point for Google Cloud Run
@http
def search_ontologies_by_request(request: Request):
    """
    HTTP Cloud Function for searching ontologies.
    Args:
        request (flask.Request): The request object.
        Can accept:
        - GET with query parameter 'search_term'
    Returns:
        JSON response with matching ontologies.
    """
    # Get query parameters
    search_term = request.args.get('search_term')
    limit = min(int(request.args.get('limit', 100)), 100)
    offset = max(int(request.args.get('offset', 0)), 0)
    
    return search_ontologies(search_term, limit, offset)