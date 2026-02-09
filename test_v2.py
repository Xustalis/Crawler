import sys
import logging
from pprint import pprint

# Add project root to path
sys.path.append('.')

from core.parser import PageParser
from core.models import ResourceType

# Setup simple logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_json_parsing():
    logger.info(">>> Testing JSON Parsing (httpbin.org/user-agent)")
    parser = PageParser()
    try:
        resources, _ = parser.parse("https://httpbin.org/user-agent")
        
        json_res = [r for r in resources if r.resource_type == ResourceType.JSON_DATA]
        if json_res:
            logger.info("✓ JSON Resource Found:")
            print(json_res[0].content)
        else:
            logger.error("✗ No JSON resource found!")
            for r in resources:
                print(f"Found: {r.resource_type} - {r.url}")
    except Exception as e:
        logger.error(f"Error: {e}")

def test_text_extraction_and_pagination():
    logger.info("\n>>> Testing Text & Pagination (quotes.toscrape.com)")
    parser = PageParser()
    try:
        resources, links = parser.parse("https://quotes.toscrape.com")
        
        # Check text
        texts = [r for r in resources if r.resource_type == ResourceType.RICH_TEXT]
        logger.info(f"Found {len(texts)} quotes.")
        if texts:
            logger.info("Sample Quote:")
            pprint(texts[0].to_dict())
        
        # Check pagination
        logger.info(f"Found {len(links)} pagination links.")
        if links:
            logger.info(f"Next Link: {links[0]}")
        else:
            logger.warning("No pagination links found!")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_json_parsing()
    test_text_extraction_and_pagination()
