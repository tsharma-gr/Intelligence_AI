import json
import logging
from typing import List
from backend.services.llm.factory import LLMFactory
from backend.prompts import load_prompt
from backend.api.config import settings

logger = logging.getLogger("company_intelligence.query_generator")

class QueryGeneratorService:
    @staticmethod
    async def generate_queries(company_type: str, product_or_service: str, location: str) -> List[str]:
        """
        Generates search query variations based on the user's requirements and configured limits.
        """
        try:
            # Load prompt
            prompt_template = load_prompt("query_generation.md")
            
            # Format prompt
            formatted_prompt = prompt_template.format(
                company_type=company_type,
                product_or_service=product_or_service,
                location=location,
                search_query_count=settings.search_query_count
            )
            
            # Get LLM Service
            llm = LLMFactory.get_service()
            
            # Request LLM
            response_text = await llm.generate_response(
                prompt=formatted_prompt,
                system_instruction="You are an AI that generates search engine queries from user search profiles. Output JSON array of strings only."
            )
            
            # Clean response text if it has markdown formatting
            clean_text = response_text.strip()
            if "```json" in clean_text:
                parts = clean_text.split("```json")
                if len(parts) > 1:
                    clean_text = parts[1].split("```")[0].strip()
            elif "```" in clean_text:
                parts = clean_text.split("```")
                if len(parts) > 1:
                    clean_text = parts[1].strip()
            
            clean_text = clean_text.strip()
            
            # Parse JSON
            queries = json.loads(clean_text)
            if isinstance(queries, list):
                # Ensure all are strings and truncate to max requested count
                result = [str(q) for q in queries][:settings.search_query_count]
                logger.info(f"Generated search queries: {result}")
                return result
            else:
                logger.error(f"Expected list of strings from LLM, got: {queries}")
                raise ValueError("LLM response did not parse to a list")
                
        except Exception as e:
            logger.exception("Failed to generate queries using LLM, using fallbacks")
            # Fallbacks
            return [
                f"{product_or_service} {company_type} {location}",
                f"{product_or_service} manufacturer {location}",
                f"{product_or_service} supplier {location}",
                f"{product_or_service} company {location}",
                f"top {product_or_service} companies {location}"
            ]
