import scrapy
from typing import Dict, List, Iterator
from urllib.parse import urljoin
import re


class MeishiCategorySpider(scrapy.Spider):
    name = "meishi_category_spider"
    allowed_domains = [
        "m.meishichina.com",
        "i3.meishichina.com",
        "i3i620.meishichina.com",
    ]
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
                # Generate paginated URLs for each category (1-100)
                for page in range(1, 101):
                    paginated_url = f"{full_url}/{page}/"
                    yield scrapy.Request(
                        paginated_url,
                        callback=self.parse_category_page,
                        meta={"category_url": full_url},
                    )

    def parse_category_page(self, response):
        """Parse each category page to find recipe links"""
        # Extract recipe links from the category page
        recipe_links = response.css('a[href*="/recipe/"]::attr(href)').getall()

        for link in recipe_links:
            # Filter out category links and ensure we only process recipe detail pages
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
