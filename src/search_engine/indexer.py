from whoosh.index import create_in, open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.analysis import StandardAnalyzer
from jieba.analyse import ChineseAnalyzer
import json
import os
from typing import List, Dict


class RecipeIndexer:
    def __init__(self, index_dir: str = "recipe_index"):
        self.index_dir = index_dir
        self.chinese_analyzer = ChineseAnalyzer()

        # Define the schema for our search index
        self.schema = Schema(
            recipe_id=ID(stored=True),
            title=TEXT(analyzer=self.chinese_analyzer, stored=True),
            ingredients_text=TEXT(analyzer=self.chinese_analyzer, stored=True),
            steps_text=TEXT(analyzer=self.chinese_analyzer, stored=True),
            tips_text=TEXT(analyzer=self.chinese_analyzer, stored=True),
            categories_text=TEXT(analyzer=self.chinese_analyzer, stored=True),
            raw_data=STORED,  # Store the complete JSON for retrieval
        )

        # Create or open the index
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
            self.ix = create_in(index_dir, self.schema)
        else:
            self.ix = open_dir(index_dir)

    def index_recipes(self, recipes: List[Dict], mode: str = "rewrite_all"):
        """
        Index recipes with specified mode:
        - 'skip_existing': Skip recipes that already exist in the index
        - 'rewrite_all': Clear existing index and write all recipes
        """
        if mode == "rewrite_all":
            # Delete existing index and create new one
            self.ix.close()
            import shutil

            shutil.rmtree(self.index_dir)
            os.makedirs(self.index_dir)
            self.ix = create_in(self.index_dir, self.schema)

        writer = self.ix.writer()

        # Get existing recipe IDs if in skip mode
        existing_ids = set()
        if mode == "skip_existing":
            with self.ix.searcher() as searcher:
                existing_ids = {
                    doc["recipe_id"] for doc in searcher.all_stored_fields()
                }

        for recipe in recipes:
            recipe_id = str(recipe.get("recipe_id", ""))
            # Skip if recipe already exists and in skip mode
            if mode == "skip_existing" and recipe_id in existing_ids:
                continue

            # Prepare searchable text fields
            ingredients_text = self._process_ingredients(recipe.get("ingredients", {}))

            # Extract step text from step dictionaries
            steps = recipe.get("steps", [])
            if isinstance(steps[0], dict):
                steps_text = " ".join(step.get("text", "") for step in steps)
            else:
                steps_text = " ".join(str(step) for step in steps)

            tips_text = " ".join(recipe.get("tips", []))
            categories_text = " ".join(recipe.get("categories", []))

            writer.add_document(
                recipe_id=str(recipe.get("recipe_id", "")),
                title=recipe.get("title", ""),
                ingredients_text=ingredients_text,
                steps_text=steps_text,
                tips_text=tips_text,
                categories_text=categories_text,
                raw_data=recipe,
            )

        writer.commit()

    def _process_ingredients(self, ingredients: Dict) -> str:
        """Convert ingredients dictionary to searchable text"""
        text_parts = []
        for section, items in ingredients.items():
            text_parts.append(section)
            for item in items:
                text_parts.append(f"{item['name']} {item['amount']}")
        return " ".join(text_parts)

    def search(self, query: str, fields=None, page=1, per_page=10) -> Dict:
        """
        Search with pagination support
        Returns: Dict containing results and pagination info
        """
        if fields is None:
            fields = [
                "title",
                "ingredients_text",
                "steps_text",
                "tips_text",
                "categories_text",
            ]

        with self.ix.searcher() as searcher:
            parser = MultifieldParser(fields, schema=self.ix.schema)
            q = parser.parse(query)

            # Use search_page instead of search with offset
            results = searcher.search_page(q, page, pagelen=per_page)

            return {
                "items": [
                    dict(score=result.score, **result["raw_data"]) for result in results
                ],
                "pagination": {
                    "total": results.total,  # total available from search_page
                    "page": results.pagenum,
                    "per_page": results.pagelen,
                    "total_pages": results.pagecount,
                },
            }

    def search_by_category(self, category: str, page=1, per_page=10) -> Dict:
        """
        Search by category with pagination support
        """
        query = f"categories_text:{category}"
        return self.search(query, page=page, per_page=per_page)

    def get_categories_summary(self) -> Dict:
        """Get a summary of all categories and their recipe counts"""
        categories_count = {}
        with self.ix.searcher() as searcher:
            for doc in searcher.all_stored_fields():
                for category in doc["raw_data"].get("categories", []):
                    categories_count[category] = categories_count.get(category, 0) + 1
        return categories_count
