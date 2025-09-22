from functools import wraps
from typing import Optional, Callable, Any
import firebase_admin
from firebase_admin import auth, credentials, exceptions
from flask import Request, jsonify
from typing import Tuple, Dict, Any, Optional, Union

def initialize_firebase():
    """Initialize the Firebase Admin SDK if not already initialized."""
    try:
        firebase_admin.get_app()
    except ValueError:
        # Initialize with application default credentials
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)

def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token.
    
    Args:
        id_token: The Firebase ID token string to verify
        
    Returns:
        dict: The decoded token claims
        
    Raises:
        ValueError: If the token is invalid, expired, or revoked
    """
    try:
        initialize_firebase()
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except (ValueError, exceptions.FirebaseError) as e:
        raise ValueError(f"Invalid authentication token: {str(e)}")

def get_authenticated_email(request: Request) -> str:
    """
    Get the authenticated user's email from the Authorization header.
    
    Args:
        request: Flask request object
        
    Returns:
        str: The authenticated user's email
        
    Raises:
        ValueError: If authentication fails or email is not verified
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise ValueError('Authorization header is missing or invalid')
    
    id_token = auth_header.split(' ')[1]
    decoded_token = verify_firebase_token(id_token)
    
    if not decoded_token.get('email_verified', False):
        raise ValueError('Email not verified')
    
    return decoded_token['email']

def get_auth_headers_and_email(request: Optional[Request] = None, email: Optional[str] = None) -> Tuple[Dict[str, str], Union[str, Tuple[Dict[str, Any], int, Dict[str, str]]]]:
    """
    Get authentication headers and verify user authentication.
    
    Args:
        request: Flask request object (optional if email is provided)
        email: Pre-authenticated email (optional if request is provided)
        
    Returns:
        If authenticated: (headers, email)
        If authentication fails: (error_response, status_code, headers)
    """
    # Set CORS response headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type',
        'Content-Type': 'application/json'
    }
    
    # If email is already provided, return it with headers
    if email is not None:
        return headers, email
        
    # Otherwise, try to get email from request
    if request is not None:
        try:
            email = get_authenticated_email(request)
            return headers, email
        except ValueError as e:
            error_response = {
                'success': False,
                'error': str(e)
            }
            return error_response, 401, headers
    
    # If we get here, neither email nor valid request was provided
    error_response = {
        'success': False,
        'error': 'Authentication required. Please provide a valid Firebase ID token.'
    }
    return error_response, 401, headers

def firebase_auth_required(f: Callable) -> Callable:
    """
    Decorator to require Firebase authentication for a route.
    
    Args:
        f: The route function to decorate
        
    Returns:
        The decorated function that includes authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            email = get_authenticated_email(args[0] if args else kwargs.get('request'))
            # Add the authenticated email to the function's kwargs
            if 'email' in kwargs:
                kwargs['email'] = email
            else:
                kwargs['authenticated_email'] = email
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 401
    return decorated_function
