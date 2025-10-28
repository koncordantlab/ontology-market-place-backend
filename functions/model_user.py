from pydantic import BaseModel
from datetime import datetime, timezone
from pydantic import Field
from typing import List, Optional
from .n4j import get_neo4j_driver

# class User(BaseModel):
#     name: str | None = None
#     email: str | None = None
#     email_verified: bool
#     fuid : str
#     uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
#     image_url: str | None = None
#     is_public: bool = False
#     is_admin: bool = False
#     created_at: datetime
#     updated_at: datetime

#     def get_edit_ontology_uuids(self) -> List[str]:
#         """
#         Returns a list of ontology UUIDs that the user can edit.
#         Authorization is determined by checking Neo4j for Ontology nodes 
#         connected via :CREATED and/or :CAN_EDIT relationships.
        
#         Returns:
#             List[str]: List of ontology UUIDs the user can edit
#         """
#         if not self.email:
#             return []
        
#         from .n4j import get_neo4j_driver
        
#         query = """
#             MATCH (u:User {uuid: $uuid})
#             MATCH (u)-[:CREATED|CAN_EDIT]->(o:Ontology)
#             RETURN DISTINCT o.uuid as uuid
#         """
        
#         try:
#             with get_neo4j_driver() as driver:
#                 result = driver.execute_query(
#                     query,
#                     uuid=self.uuid,
#                     database_="neo4j",
#                     result_transformer_=lambda r: [record['uuid'] for record in r]
#                 )
#                 return result
#         except Exception as e:
#             print(f"Error querying edit ontology UUIDs: {str(e)}")
#             return []


#     def can_edit_ontology(self, ontology_id: str, email: str) -> bool:
#         """
#         Check if the user can edit the ontology
#         """
#         return ontology_id in self.get_edit_ontology_uuids()

def get_user_uuid_by_fuid(fuid: str) -> Optional[str]:
    """
    Get the user's UUID from Neo4j by their Firebase UID (fuid).
    
    Args:
        fuid: Firebase User ID
        
    Returns:
        User's UUID if found, None otherwise
    """
    if not fuid:
        return None
    
    from .n4j import get_neo4j_driver
    
    query = """
        MATCH (u:User {fuid: $fuid})
        RETURN u.uuid as uuid
    """
    
    try:
        with get_neo4j_driver() as driver:
            result = driver.execute_query(
                query,
                fuid=fuid,
                database_="neo4j",
                result_transformer_=lambda r: (r.single() or {}).get('uuid')
            )
            return result
    except Exception as e:
        print(f"Error querying user UUID by fuid: {str(e)}")
        return None



def get_edit_ontologies_by_uuid(uuid: str) -> List[str]:
    """
    Returns a list of ontology UUIDs that the user can edit by their UUID.
    Authorization is determined by checking Neo4j for Ontology nodes 
    connected via :CREATED and/or :CAN_EDIT relationships.
    
    Args:
        uuid: User UUID
        
    Returns:
        List[str]: List of ontology UUIDs the user can edit
    """
    if not uuid:
        return []
    
    
    query = """
        MATCH (u:User {uuid: $uuid})
        MATCH (u)-[:CREATED|CAN_EDIT]->(o:Ontology)
        RETURN DISTINCT o.uuid as uuid
    """
    
    try:
        with get_neo4j_driver() as driver:
            result = driver.execute_query(
                query,
                uuid=uuid,
                database_="neo4j",
                result_transformer_=lambda r: [record['uuid'] for record in r]
            )
            return result
    except Exception as e:
        print(f"Error querying edit ontology UUIDs: {str(e)}")
        return []


def get_delete_ontologies_by_uuid(uuid: str) -> List[str]:
    """
    Returns a list of ontology UUIDs that the user can delete by their UUID.
    Authorization is determined by checking Neo4j for Ontology nodes 
    connected via :CREATED and/or :CAN_DELETE relationships.
    
    Args:
        uuid: User UUID
        
    Returns:
        List[str]: List of ontology UUIDs the user can delete
    """
    if not uuid:
        return []
    
    query = """
        MATCH (u:User {uuid: $uuid})
        MATCH (u)-[:CREATED|CAN_DELETE]->(o:Ontology)
        RETURN DISTINCT o.uuid as uuid
    """
    
    try:
        with get_neo4j_driver() as driver:
            result = driver.execute_query(
                query,
                uuid=uuid,
                database_="neo4j",
                result_transformer_=lambda r: [record['uuid'] for record in r]
            )
            return result
    except Exception as e:
        print(f"Error querying delete ontology UUIDs: {str(e)}")
        return []


def can_user_edit_ontology(uuid: str, ontology_id: str) -> dict:
    """
    Check if the user can edit the ontology by their UUID.
    
    Args:
        uuid: User UUID
        ontology_id: Ontology UUID to check
        
    Returns:
        Dictionary with success status and message
    """
    if not uuid:
        return {
            "success": False,
            "message": "User authentication required",
            "data": None
        }
    
    try:
        edit_uuids = get_edit_ontologies_by_uuid(uuid)
        can_edit = ontology_id in edit_uuids
        
        return {
            "success": True,
            "message": "Authorization check complete",
            "data": {
                "ontology_id": ontology_id,
                "can_edit": can_edit
            }
        }
    except Exception as e:
        print(f"Error checking edit permission: {str(e)}")
        return {
            "success": False,
            "message": f"Failed authorization check: {str(e)}",
            "data": None
        }


def can_user_delete_ontology(uuid: str, ontology_id: str) -> dict:
    """
    Check if the user can delete the ontology by their UUID.
    
    Args:
        uuid: User UUID
        ontology_id: Ontology UUID to check
        
    Returns:
        Dictionary with success status and message
    """
    if not uuid:
        return {
            "success": False,
            "message": "User authentication required",
            "data": None
        }
    
    try:
        delete_uuids = get_delete_ontologies_by_uuid(uuid)
        can_delete = ontology_id in delete_uuids
        
        return {
            "success": True,
            "message": "Authorization check complete",
            "data": {
                "ontology_id": ontology_id,
                "can_delete": can_delete
            }
        }
    except Exception as e:
        print(f"Error checking delete permission: {str(e)}")
        return {
            "success": False,
            "message": f"Failed authorization check: {str(e)}",
            "data": None
        }