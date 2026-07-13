import json
import logging
from typing import List
from backend.models.company import Qualification, Evidence
from backend.crawler.models import CrawledPage
from backend.services.llm.factory import LLMFactory
from backend.prompts import load_prompt

logger = logging.getLogger("company_intelligence.qualification")

class QualificationService:
    @staticmethod
    async def qualify_company(
        company_name: str,
        company_type: str,
        product_or_service: str,
        location: str,
        pages: List[CrawledPage]
    ) -> Qualification:
        """
        Qualifies a company by sending its page text contents to the LLM
        and parses the returned structured JSON.
        """
        if not pages:
            return Qualification(
                qualified=False,
                reason="No website content could be fetched or discovered.",
                confidence=100,
                evidence=[]
            )
            
        try:
            # Prepare consolidated website content text block
            content_blocks = []
            for p in pages:
                content_blocks.append(f"--- PAGE: {p.page_type} ({p.url}) ---\n{p.content}\n")
            website_content = "\n".join(content_blocks)
            
            # Load prompt
            prompt_template = load_prompt("qualification.md")
            
            # Format prompt
            formatted_prompt = prompt_template.format(
                company_type=company_type,
                product_or_service=product_or_service,
                location=location,
                website_content=website_content
            )
            
            # Get LLM Service
            llm = LLMFactory.get_service()
            
            # Request LLM
            response_text = await llm.generate_response(
                prompt=formatted_prompt,
                system_instruction=f"You are an AI auditor qualifying the company '{company_name}' based on specific criteria. Output JSON only."
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
            
            # Parse JSON with strict=False to tolerate unescaped control characters
            qual_data = json.loads(clean_text, strict=False)
            
            # Construct and validate with Pydantic
            evidence_list = []
            for ev in qual_data.get("evidence", []):
                evidence_list.append(Evidence(
                    page=ev.get("page", ""),
                    quote=ev.get("quote", "")
                ))
                
            return Qualification(
                qualified=bool(qual_data.get("qualified", False)),
                reason=str(qual_data.get("reason", "No reason provided.")),
                confidence=int(qual_data.get("confidence", 50)),
                evidence=evidence_list
            )
            
        except Exception as e:
            logger.exception(f"Failed to qualify company {company_name} using LLM")
            # Return a default negative qualification with error description
            return Qualification(
                qualified=False,
                reason=f"Failed to analyze company due to system error: {str(e)}",
                confidence=0,
                evidence=[]
            )
