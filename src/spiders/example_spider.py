from .base_spider import BaseSpider

class ExampleSpider(BaseSpider):
    name = 'example_spider'
    
    def parse(self, response):
        """
        Example parsing method - customize based on your needs
        """
        for article in response.css('article'):
            yield {
                'title': article.css('h2::text').get(),
                'content': article.css('p::text').get(),
                'link': article.css('a::attr(href)').get(),
            }
        
        # Follow pagination links
        next_page = response.css('a.next-page::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse) 