BOT_NAME = "trump_vs_harris"

SPIDER_MODULES = ["src.spiders"]
NEWSPIDER_MODULE = "src.spiders"

# Crawl responsibly by identifying yourself
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False


# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 543,
    "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
}

# Configure item pipelines
ITEM_PIPELINES = {
    "src.pipelines.MeishiImagePipeline": 1,
    # "src.pipelines.MeishiPipeline": 300,
}

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = "httpcache"

# Add meishichina specific settings
CONCURRENT_REQUESTS_PER_DOMAIN = 10
DOWNLOAD_DELAY = 2  # Be polite with the server
RANDOMIZE_DOWNLOAD_DELAY = True

# Export feed in utf-8 encoding
FEED_EXPORT_ENCODING = "utf-8"

# Images settings
IMAGES_STORE = "images3"
IMAGES_URLS_FIELD = "image_urls"
IMAGES_RESULT_FIELD = "image_paths"

# Download settings
DOWNLOAD_TIMEOUT = 180
DOWNLOAD_FAIL_ON_DATALOSS = False

# Allow image domains
IMAGES_DOMAINS = ["meishichina.com"]

# Disable the offsite middleware for image domains
SPIDER_MIDDLEWARES = {"scrapy.spidermiddlewares.offsite.OffsiteMiddleware": None}

# Add custom headers for image requests
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Images Pipeline Settings
MEDIA_ALLOW_REDIRECTS = True
