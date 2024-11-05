import json
import scrapy
from typing import Dict, List, Iterator
from urllib.parse import urljoin
import re
from datetime import datetime


class MeishiSelectedSpider(scrapy.Spider):
    name = "meishi_selected_spider"
    allowed_domains = ["meishichina.com", "!i8.meishichina.com"]

    def start_requests(self):
        """Generate initial request for the main recipe page"""
        yield scrapy.Request(
            "https://m.meishichina.com/recipe/", callback=self.parse_categories
        )

    def parse_categories(self, response):
        """Parse the main recipe page to extract categories"""
        # Load quota configuration
        with open("meishi_quota.json") as f:
            quotas = json.load(f)

        # Handle "all" type URLs (hot and popular)
        hot_quota = quotas.get("all.hot", 0)
        pop_quota = quotas.get("all.pop", 0)

        # Parse categories directly from the page
        category_links = response.css(
            'a[href*="/recipe/category/"]::attr(href)'
        ).getall()
        for link in category_links:
            cat_key = link.split("/category/")[-1].strip("/")

            quota = quotas.get(
                f"category.{cat_key}", quotas.get("category._default", 5)
            )
            if quota < 1:
                continue

            yield scrapy.Request(
                f"https://m.meishichina.com/recipe/category/{cat_key}/1/",
                callback=self.parse_recipe_list,
                meta={
                    "category": cat_key,
                    "current_page": 1,
                    "quota": quota,
                    "page_type": "category",
                },
            )

        # Handle both hot and popular pages
        for page_type, quota in [("hot", hot_quota), ("pop", pop_quota)]:
            if quota < 1:
                continue
            yield scrapy.Request(
                f"https://m.meishichina.com/recipe/all/{page_type}/1/",
                callback=self.parse_recipe_list,
                meta={"page_type": page_type, "current_page": 1, "quota": quota},
            )

    def parse_recipe_list(self, response):
        """Parse the recipe list pages (both category and all types)"""
        # Log the URL with additional context
        with open("recipe_list_urls.log", "a", encoding="utf-8") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"{timestamp}\t{response.url}\n")

        recipe_links = response.css('a[href*="/recipe/"]::attr(href)').getall()

        # Check if we have any recipes on this page
        has_recipes = any(
            "/category/" not in link and re.match(r".*/recipe/\d+/?$", link)
            for link in recipe_links
        )

        # Get pagination metadata
        page_type = response.meta.get("page_type")
        category = response.meta.get("category")
        current_page = response.meta.get("current_page", 1)
        quota = response.meta.get("quota", 0)

        # If we have recipes and haven't reached quota, request next page
        if has_recipes and current_page < quota:
            next_page = current_page + 1
            if page_type != "category":  # For hot/pop pages
                next_url = (
                    f"https://m.meishichina.com/recipe/all/{page_type}/{next_page}/"
                )
            else:  # For category pages
                next_url = (
                    f"https://m.meishichina.com/recipe/category/{category}/{next_page}/"
                )

            yield scrapy.Request(
                next_url,
                callback=self.parse_recipe_list,
                meta={
                    "page_type": page_type,
                    "category": category,
                    "current_page": next_page,
                    "quota": quota,
                },
            )

        # Process current page recipes
        for link in recipe_links:
            if "/category/" not in link and re.match(r".*/recipe/\d+/?$", link):
                full_url = response.urljoin(link)
                yield scrapy.Request(full_url, callback=self.parse_recipe)

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
        item = {
            "title": title or "",  # Defensive programming for other fields too
            "recipe_id": recipe_id,
            "ingredients": ingredients_data or {},
            "steps": steps or [],
            "tips": tips or [],
            "categories": categories or [],
            "detail_url": response.url,
            "image_url": image_url,
        }
        yield item
