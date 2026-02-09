from core.parser import PageParser
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.DEBUG)

def debug_quotes():
    url = "https://quotes.toscrape.com"
    parser = PageParser()
    response = parser.network.get(url)
    
    if not response:
        print("Failed to fetch!")
        return

    print(f"Status Code: {response.status_code}")
    print(f"Content Type: {response.headers.get('Content-Type')}")
    print(f"Content Length: {len(response.text)}")
    print("--- First 1000 chars ---")
    print(response.text[:1000])
    print("------------------------")
    
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Debug quotes
    quotes = soup.find_all(class_='quote')
    print(f"Found {len(quotes)} quote elements")
    
    if quotes:
        q = quotes[0]
        print("First quote HTML:")
        print(q.prettify())
        
        text = q.find(class_='text')
        print(f"Text element: {text}")
    
    # Debug pagination
    next_link = soup.find(class_='next')
    print(f"Next link class='next': {next_link}")
    
    next_a = soup.find('a', string="Next")
    print(f"Next link string='Next': {next_a}")
    
    links = parser.get_pagination_links(soup, url)
    print(f"Extracted Links: {links}")

if __name__ == "__main__":
    debug_quotes()
