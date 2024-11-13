import scrapy
from scrapy.pipelines.images import ImagesPipeline
from urllib.parse import urlparse
import os
import uuid


class MeishiPipeline:
    def process_item(self, item, spider):
        print("MeishiPipeline processing item:", item.get("title"))  # Debug print
        # Check if we have raw_ingredients (from list page)
        if "raw_ingredients" in item:
            raw_ingredients = item["raw_ingredients"]
            if raw_ingredients:
                item["raw_ingredients_list"] = [
                    ing.strip() for ing in raw_ingredients.split("、")
                ]

        # The detailed ingredients are already structured in item['ingredients']
        return item


class MeishiImagePipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": item.get("detail_url", "https://m.meishichina.com/"),
        }
        
        # Handle main recipe image
        if item.get("image_url"):
            yield scrapy.Request(
                item["image_url"],
                headers=headers,
                meta={
                    "recipe_id": item["recipe_id"],
                    "image_type": "main",
                },
                dont_filter=True,
                errback=self.download_error,
            )
        
        # Handle step images
        if item.get("steps"):
            headers["Referer"] = item.get("detail_url", "https://m.meishichina.com/")
            for idx, step in enumerate(item["steps"]):
                if step.get("image"):
                    yield scrapy.Request(
                        step["image"],
                        headers=headers,
                        meta={
                            "recipe_id": item["recipe_id"],
                            "image_type": "step",
                            "step_index": idx,
                            "step_text": step.get("text", "")
                        },
                        dont_filter=True,
                        errback=self.download_error,
                    )

    def download_error(self, failure):
        print(f"Error downloading image: {failure.value}")
        return None

    def file_path(self, request, response=None, info=None, *, item=None):
        try:
            recipe_id = request.meta.get("recipe_id")
            image_type = request.meta.get("image_type")
            
            path = urlparse(request.url).path
            ext = os.path.splitext(path)[1] or ".jpg"
            
            if image_type == "main":
                return f'recipe_images/{recipe_id}/main{ext}'
            elif image_type == "step":
                step_index = request.meta.get("step_index")
                return f'recipe_images/{recipe_id}/step_{step_index}{ext}'
            
            return f"recipe_images/error_{uuid.uuid4()}{ext}"
        except Exception as e:
            print(f"Error in file_path: {e}")
            return f"recipe_images/error_{uuid.uuid4()}.jpg"

    def item_completed(self, results, item, info):
        try:
            image_paths = []
            for ok, x in results:
                if ok and x and isinstance(x, dict) and "path" in x:
                    image_paths.append(x["path"])

            if image_paths:
                item["image_paths"] = image_paths
            else:
                print(f"No valid image paths for {item.get('title')}")
        except Exception as e:
            print(f"Error processing image results: {e}")

        return item
