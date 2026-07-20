import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger("company_intelligence.crawler.extractor")

class ContentExtractor:
    @staticmethod
    def extract_clean_text(html_content: str) -> str:
        """
        Removes headers, footers, navigation, scripts, ads, and cookies banners.
        Returns clean structural text content of the page.
        """
        if not html_content:
            return ""
            
        try:
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception as e:
            logger.error(f"Failed to parse HTML in extractor: {e}")
            return ""
        
        # Remove structural tags that are purely noise
        tags_to_remove = ["script", "style", "noscript", "svg", "iframe", "form"]
        for tag in soup.find_all(tags_to_remove):
            tag.decompose()
            
        # Select common boilerplate classes / IDs to remove (cookie banners, menus)
        boilerplate_pattern = re.compile(
            r"cookie|consent|banner|menu|social|share|widget|advert|popup|modal", 
            re.IGNORECASE
        )
        
        for element in soup.find_all(True):
            if getattr(element, "attrs", None) is None:
                continue
                
            element_id = element.get("id", "")
            
            # class can be a string or a list of strings
            class_attr = element.get("class", [])
            if isinstance(class_attr, list):
                element_classes = " ".join(class_attr)
            else:
                element_classes = str(class_attr)
            
            if (element_id and boilerplate_pattern.search(str(element_id))) or \
               (element_classes and boilerplate_pattern.search(element_classes)):
                element.decompose()
                
        # Get raw text content
        text = soup.get_text(separator="\n")
        
        # Process and clean lines
        lines = []
        for line in text.splitlines():
            line_str = line.strip()
            # Ignore short lines containing boilerplate or empty lines
            if line_str and len(line_str) > 10:
                lines.append(line_str)
                
        cleaned_text = "\n".join(lines)
        return cleaned_text
