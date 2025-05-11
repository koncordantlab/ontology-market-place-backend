from fastapi import FastAPI
from typing import List, Optional
from pydantic import BaseModel
from functions.search_ontologies import search_ontologies
from functions.add_ontologies import add_ontologies
from functions.model_ontology import Ontology, NewOntology, OntologyResponse
from flask import Request as FlaskRequest
import os

app = FastAPI(title="Ontology Marketplace API")


@app.get("/search_ontologies", response_model=OntologyResponse)
async def search_ontologies_endpoint(
    search_term: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Search for ontologies based on query parameters
    """
    return search_ontologies(search_term, limit, offset)

@app.post("/add_ontologies", response_model=OntologyResponse)
async def add_ontologies_endpoint(ontologies: List[NewOntology]):
    """
    Add new ontologies to the system
    """
    try:
        ontology_dicts = [onto.model_dump() for onto in ontologies]
        return add_ontologies(ontology_dicts)
    except Exception as e:
        return OntologyResponse(
            success=False,
            message=f"Failed to process request: {str(e)}",
            data=None
        )

@app.delete("/delete_ontologies", response_model=OntologyResponse)
async def delete_ontologies_endpoint(ontology_ids: List[str]):
    """
    Delete ontologies by their IDs
    """
    # TODO: Implement delete logic
    return OntologyResponse(
        success=True,
        message="Delete functionality to be implemented",
        data={"deleted_ids": ontology_ids}
    )

@app.put("/update_ontology/{ontology_id}", response_model=OntologyResponse)
async def update_ontology_endpoint(ontology_id: str, ontology: Ontology):
    """
    Update an existing ontology
    """
    # TODO: Implement update logic
    return OntologyResponse(
        success=True,
        message="Update functionality to be implemented",
        data={"ontology_id": ontology_id, "updated_data": ontology.dict()}
    )

@app.post("/like_ontology/{ontology_id}", response_model=OntologyResponse)
async def like_ontology_endpoint(ontology_id: str):
    """
    Like an ontology
    """
    # TODO: Implement like logic
    return OntologyResponse(
        success=True,
        message="Like functionality to be implemented",
        data={"ontology_id": ontology_id}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
