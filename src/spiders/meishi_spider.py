import scrapy
from typing import (
    Iterator,
    Dict,
)
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
                    )

        # Handle pagination by incrementing page number
        current_page = int(response.url.split("page=")[1])
        next_page = current_page + 1
        next_url = f"https://m.meishichina.com/ajax.php?ac=m&op=getTimeLineList&page={next_page}"

        # Continue to next page if we have recipes in current response
        if recipes:
            yield scrapy.Request(next_url)

    def parse_recipe(self, response) -> Iterator[Dict]:
        # Extract recipe_id from URL
        recipe_id = response.url.split("/recipe/")[-1].rstrip("/")

        # Get title - check both direct text and anchor text within h1
        title = (
            response.xpath("//h1/a/text()").get() or response.xpath("//h1/text()").get()
        )

        ingredients_data = {}

        # Find all ingredient sections (主料, 辅料, 配料 etc.)
        ingredient_sections = response.xpath('//div[@class="rbox"]//h5')

        for section in ingredient_sections:
            # Get section name (e.g., "主料", "辅料", "配料")
            section_name = section.xpath("./text()").get()
            if not section_name:
                continue

            # Get ingredients under this section - more generic approach
            ingredients = []
            # Just target li elements and find spans within them
            ingredient_elements = section.xpath("./following-sibling::ul[1]/li")

            for ingredient in ingredient_elements:
                # Get all spans within the li element, regardless of parent structure
                spans = ingredient.xpath(".//span/text()").getall()
                if len(spans) >= 2:
                    name, amount = spans[0], spans[1]
                    ingredients.append({"name": name.strip(), "amount": amount.strip()})

            if ingredients:
                ingredients_data[section_name] = ingredients

        # Get cooking steps with images - updated parsing logic
        steps = []
        step_elements = response.xpath('//ul[@class="steplist"]/li')
        for step in step_elements:
            step_text = step.xpath("./div/text()").get().strip()
            # Remove the step number (e.g., "1.", "2.", etc.)
            step_text = (
                ".".join(step_text.split(".")[1:]).strip()
                if "." in step_text
                else step_text
            )

            # Get the image URL from data-src attribute
            image_url = step.xpath("./img/@data-src").get()

            if step_text:
                steps.append({"text": step_text, "image": image_url})

        # Get tips (小窍门 & 温馨提示)
        tips_container = response.xpath(
            '//div[contains(@class, "textbox")][.//h3[contains(text(), "窍门") or contains(text(), "提示")]]//div/text()'
        ).getall()
        tips = []
        for tip in tips_container:
            # Split by line breaks and process each tip
            tip_lines = tip.strip().split("\n")
            tips.extend([t.strip() for t in tip_lines if t.strip()])

        # Get categories
        categories = response.xpath(
            '//div[contains(@class, "textbox")][contains(text(), "分类：")]//a/text()'
        ).getall()
        categories = [cat.strip() for cat in categories if cat.strip()]

        # Get full size image with validation
        image_url = (
            response.css("div.row.mb20 img::attr(src)").get() or ""
        )  # Default to empty string

        # Combine all data with validated fields
        yield {
            "title": title or "",  # Defensive programming for other fields too
            "recipe_id": recipe_id,
            "ingredients": ingredients_data or {},
            "steps": steps or [],
            "tips": tips or [],
            "categories": categories or [],
            "detail_url": response.url,
            "image_url": image_url,
        }
