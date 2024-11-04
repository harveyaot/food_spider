import scrapy
from typing import Iterator
from typing import Dict, List
import json


class MeishiSpider(scrapy.Spider):
    name = "meishi_spider"
    allowed_domains = [
        "m.meishichina.com",
        "i3.meishichina.com",
        "i3i620.meishichina.com",
    ]
    start_urls = ["https://m.meishichina.com/ajax.php?ac=m&op=getTimeLineList&page=1"]

    def parse(self, response) -> Iterator[dict]:
        # Parse JSON response
        data = json.loads(response.text)
        recipes = data.get("data", [])

        for recipe in recipes:
            # Only process items that are recipes and have remark as "菜谱"
            if recipe.get("type") == "recipe" and recipe.get("remark") == "菜谱":
                recipe_url = recipe.get("wapurl")
                if recipe_url:
                    yield scrapy.Request(
                        url=recipe_url,
                        callback=self.parse_recipe,
                        cb_kwargs={
                            "list_data": {
                                "title": recipe.get("subject"),
                                "raw_ingredients": recipe.get("description"),
                                "image_url": recipe.get("pic640"),
                                "recipe_id": recipe.get("subid"),
                            }
                        },
                    )

        # Handle pagination by incrementing page number
        current_page = int(response.url.split("page=")[1])
        next_page = current_page + 1
        next_url = f"https://m.meishichina.com/ajax.php?ac=m&op=getTimeLineList&page={next_page}"

        # Continue to next page if we have recipes in current response
        if recipes:
            yield scrapy.Request(next_url)

    def parse_recipe(self, response, list_data: Dict) -> Iterator[Dict]:
        ingredients_data = {}

        # Find all ingredient sections (主料, 辅料, 配料 etc.)
        ingredient_sections = response.xpath('//div[@class="rbox"]//h5')

        for section in ingredient_sections:
            # Get section name (e.g., "主料", "辅料", "配料")
            section_name = section.xpath("./text()").get()
            if not section_name:
                continue

            # Get ingredients under this section
            ingredients = []
            ingredient_elements = section.xpath("./following-sibling::ul[1]/li/a")

            for ingredient in ingredient_elements:
                # Extract both name and amount
                spans = ingredient.xpath(".//span/text()").getall()
                if len(spans) >= 2:
                    ingredients.append({"name": spans[0], "amount": spans[1]})

            # Add to ingredients data using section name as key
            ingredients_data[section_name] = ingredients

        # Get cooking steps
        steps = []
        step_elements = response.xpath('//div[contains(@class, "steps")]//li')
        for step in step_elements:
            step_text = step.xpath(".//text()").get()
            if step_text:
                steps.append(step_text.strip())

        # Get tips (小窍门)
        tips = response.xpath('//div[contains(@class, "tips")]//text()').getall()
        tips = [tip.strip() for tip in tips if tip.strip()]

        # Get categories
        categories = response.xpath(
            '//div[contains(@class, "recipe-cats")]//text()'
        ).getall()
        categories = [cat.strip() for cat in categories if cat.strip()]

        # Add full size image parsing
        full_image = response.css("div.row.mb20 img::attr(src)").get()
        if full_image:
            list_data["image_url"] = full_image

        # Combine all data
        yield {
            **list_data,
            "ingredients": ingredients_data,
            "steps": steps,
            "tips": tips,
            "categories": categories,
            "detail_url": response.url,
        }
