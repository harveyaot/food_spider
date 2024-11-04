import scrapy
from typing import Dict, List, Iterator
from urllib.parse import urljoin
import re


class MeishiCategorySpider(scrapy.Spider):
    name = "meishi_category_spider"
    allowed_domains = ["meishichina.com"]
    start_urls = ["https://m.meishichina.com/recipe/"]

    def parse(self, response):
        """Parse the main category page to find all category links"""
        # Find all links that start with /recipe/category/
        category_links = response.css(
            'a[href*="/recipe/category/"]::attr(href)'
        ).getall()

        # Filter and process unique category links
        unique_categories = set()
        for link in category_links:
            # Convert relative URLs to absolute URLs if necessary
            full_url = response.urljoin(link)
            if full_url not in unique_categories:
                unique_categories.add(full_url)
                # Start with page 1 and handle pagination dynamically
                yield scrapy.Request(
                    f"{full_url}/1/",
                    callback=self.parse_category_page,
                    meta={"category_url": full_url, "current_page": 1},
                    dont_filter=False,  # Enable duplicate filtering
                )

    def parse_category_page(self, response):
        """Parse each category page to find recipe links"""
        # Check if we got redirected (indicating invalid page)
        if response.url != response.request.url:
            return

        # Extract recipe links from the category page
        recipe_links = response.css('a[href*="/recipe/"]::attr(href)').getall()

        # If we found valid recipe links, continue to next page
        if recipe_links:
            current_page = response.meta["current_page"]
            next_page = current_page + 1

            # Only continue if we're below page 100
            if next_page <= 100:
                category_url = response.meta["category_url"]
                yield scrapy.Request(
                    f"{category_url}/{next_page}/",
                    callback=self.parse_category_page,
                    meta={"category_url": category_url, "current_page": next_page},
                    dont_filter=False,
                )

        # Process recipe links
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
