from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional
import uuid

class OntologyResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class NewOntology(BaseModel):
    title: str
    file_url: str
    description: str | None = None
    node_count: int | None = None
    relationship_count: int | None = None
    is_public: bool = False

class UpdateOntology(BaseModel):
    title: str | None = None
    file_url: str | None = None
    description: str | None = None
    node_count: int | None = None
    relationship_count: int | None = None
    is_public: bool | None = None

class Ontology(BaseModel):
    uid: str
    title: str
    file_url: str
    description: str | None = None
    node_count: int | None = None
    relationship_count: int | None = None
    is_public: bool = False
    created_time: datetime

    @classmethod
    def from_new_ontology(cls, new_ontology: NewOntology) -> 'Ontology':
        """
        Create an Ontology from a NewOntology with auto-generated fields.
        
        Args:
            new_ontology: The NewOntology instance to convert
            
        Returns:
            A new Ontology instance with auto-generated uid and created_time
        """
        return cls(
            uid=str(uuid.uuid4()),
            created_time=datetime.now(timezone.utc),
            **new_ontology.model_dump()
        )

    @classmethod
    def from_new_ontologies(cls, new_ontologies: list[dict]) -> list['Ontology']:
        """
        Convert a list of NewOntology dictionaries to Ontology objects.
        
        Args:
            new_ontologies: List of dictionaries representing NewOntology objects
            
        Returns:
            List of Ontology objects with auto-generated fields
            
        Raises:
            ValidationError: If any of the input dictionaries are invalid
        """
        return [
            cls.from_new_ontology(NewOntology(**onto_data))
            for onto_data in new_ontologies
        ]