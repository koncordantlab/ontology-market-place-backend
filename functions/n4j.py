from dotenv import load_dotenv
from neo4j import GraphDatabase
import os

# Load environment variables
load_dotenv()

# Neo4j connection configuration from environment variables
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

if not NEO4J_PASSWORD:
    raise ValueError("NEO4J_PASSWORD environment variable is required")

def get_neo4j_driver():
    """Create and return a Neo4j driver instance"""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))