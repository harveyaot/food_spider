from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import json
from .indexer import RecipeIndexer
from math import ceil

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the indexer
indexer = RecipeIndexer()

# Load initial data
with open("data/recipe_selected_v3_samples.json", "r", encoding="utf-8") as f:
    recipes = json.load(f)
    indexer.index_recipes(recipes)


@app.get("/search/")
async def search(
    q: str = Query(..., description="Search query"),
    fields: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=50, description="Items per page"),
):
    results = indexer.search(q, fields=fields, page=page, per_page=per_page)
    return results


@app.get("/categories/")
async def get_categories():
    return {"categories": indexer.get_categories_summary()}


@app.get("/recipes/by_category/{category}")
async def get_recipes_by_category(
    category: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=50, description="Items per page"),
):
    results = indexer.search_by_category(category, page=page, per_page=per_page)
    return results


@app.get("/recipe/{recipe_id}")
async def get_recipe(recipe_id: str):
    results = indexer.search(f"recipe_id:{recipe_id}", per_page=1)
    if not results:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"recipe": results["items"][0]}
