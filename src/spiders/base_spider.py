import scrapy

class BaseSpider(scrapy.Spider):
    name = 'base_spider'
    
    def start_requests(self):
        urls = [
            # Add your target URLs here
            'https://example.com',
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        """Override this method in your specific spiders"""
        yield {
            'url': response.url,
            'title': response.css('title::text').get(),
        } 