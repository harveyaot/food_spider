import json
import scrapy


class MeishiImageDownloaderSpider(scrapy.Spider):
    name = "meishi_image_spider"
    start_urls = ["https://m.meishichina.com/"]
    allowed_domains = ["meishichina.com", "!i8.meishichina.com"]
    
    def parse(self, response):
        with open('data/recipe_selected_v3.json', 'r', encoding='utf-8') as f:
            recipes = json.load(f)
            
        for recipe in recipes:
            yield {
                "recipe_id": recipe.get("recipe_id", "unknown"),
                "steps": recipe.get("steps", [])[:10],
                "detail_url": recipe.get("detail_url", "")
            }

