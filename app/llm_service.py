import google.generativeai as genai
import json
import os
from typing import Dict, Any
from dotenv import load_dotenv
from app.models import InsightsRequest, InsightsResponse, RiskLevel

load_dotenv()


class LLMService:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            'gemini-2.5-flash',
            generation_config={
                'temperature': 0.2,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 4096,
            }
        )
    
    def _build_system_prompt(self) -> str:
        return """You are a procurement analytics expert specializing in supplier risk assessment and sourcing strategy for manufacturing companies.

Your task is to analyze supplier data and generate actionable insights for procurement executives.

CRITICAL REQUIREMENTS:
1. You must respond ONLY with valid JSON matching the exact schema provided
2. No explanatory text before or after the JSON
3. No markdown formatting or code blocks
4. All risk assessments must be data-driven and based on the input metrics
5. Focus on actionable, executive-level insights suitable for mobile dashboards

ANALYSIS FRAMEWORK:
- Assess concentration risk (single source dependencies, spend distribution)
- Evaluate delivery performance and operational risk
- Identify contract timing urgencies (expiring within 6 months = high priority)
- Consider geographic diversification
- Generate concrete, time-bound action items"""

    def _build_user_prompt(self, request: InsightsRequest) -> str:
        suppliers_json = json.dumps([s.dict() for s in request.suppliers], indent=2)
        
        return f"""Analyze the following procurement data and generate structured insights.

CATEGORY: {request.category}

SUPPLIER DATA:
{suppliers_json}

Generate a JSON response with this EXACT structure:
{{
  "category": "string (the category name)",
  "overall_risk_level": "Low OR Medium OR High",
  "key_risks": ["risk 1", "risk 2", "risk 3"],
  "negotiation_levers": ["lever 1", "lever 2", "lever 3"],
  "recommended_actions_next_90_days": ["action 1", "action 2", "action 3"],
  "confidence_score": 0.XX
}}

SCORING GUIDELINES:
- overall_risk_level: "High" if single-source dependency exists OR contracts expiring within 3 months OR delivery performance < 90%
- overall_risk_level: "Medium" if moderate concerns (contracts 3-6 months, delivery 90-95%, concentrated spend)
- overall_risk_level: "Low" if well-diversified, strong performance, adequate contract runway
- key_risks: Must identify 3-5 specific risks based on data (concentration, timing, performance, geographic)
- negotiation_levers: Must identify 3-5 specific leverage points (competitive alternatives, volume, contract timing, performance gaps)
- recommended_actions_next_90_days: Must provide 3-5 concrete, time-bound actions prioritized by urgency

Calculate confidence_score based on these factors:
- Start with base 0.85 (we have complete, structured data)
- Deduct 0.05 if only 1-2 suppliers (limited comparison basis)
- Deduct 0.05 if any data appears inconsistent or unclear
- Deduct 0.10 if analysis requires significant assumptions
- Add 0.05 if there are clear, unambiguous risk signals

Typical ranges:
- 0.90-0.95: Complete data, 3+ suppliers, clear patterns
- 0.80-0.89: Good data quality, some minor gaps or ambiguity
- 0.70-0.79: Acceptable data, but requires some assumptions

For this specific dataset with 3 suppliers and complete fields, confidence should be 0.85-0.92.

IMPORTANT: Ensure your JSON is complete and properly closed. Do not truncate the response.

Respond with ONLY the JSON object, no other text."""

    def generate_insights(self, request: InsightsRequest) -> InsightsResponse:
        try:
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(request)
            
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            print(f"Making API call to Google Gemini...")
            
            response = self.model.generate_content(full_prompt)
            
            response_text = response.text.strip()
            
            print(f"Received response from LLM: {response_text[:200]}...")
            
            if not response_text.endswith('}'):
                print("WARNING: Response appears truncated, attempting to fix...")
                open_braces = response_text.count('{')
                close_braces = response_text.count('}')
                if open_braces > close_braces:
                    response_text += '}' * (open_braces - close_braces)
            
            response_text = self._clean_json_response(response_text)
            
            response_data = json.loads(response_text)
            
            response_data = self._validate_and_fix_response(response_data, request.category)
            
            insights_response = InsightsResponse(**response_data)
            
            return insights_response
            
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {str(e)}")
            if 'response_text' in locals():
                print(f"Response text was: {response_text}")
            raise Exception(f"Failed to parse LLM response as JSON: {str(e)}")
        except AttributeError as e:
            print(f"AttributeError: {str(e)}")
            if 'response' in locals():
                print(f"Response object: {response}")
                print(f"Response dir: {dir(response)}")
            raise Exception(f"Error accessing response attributes: {str(e)}")
        except Exception as e:
            print(f"Unexpected Error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error generating insights: {str(e)}")
    
    def _clean_json_response(self, text: str) -> str:
        text = text.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        return text.strip()
    
    def _validate_and_fix_response(self, data: Dict[str, Any], category: str) -> Dict[str, Any]:
        if "category" not in data or not data["category"]:
            data["category"] = category
        
        if "overall_risk_level" not in data:
            data["overall_risk_level"] = "Medium"
        else:
            risk_level = data["overall_risk_level"]
            if risk_level not in ["Low", "Medium", "High"]:
                data["overall_risk_level"] = "Medium"
        
        for list_field in ["key_risks", "negotiation_levers", "recommended_actions_next_90_days"]:
            if list_field not in data or not isinstance(data[list_field], list) or len(data[list_field]) == 0:
                data[list_field] = [f"Analysis pending for {list_field.replace('_', ' ')}"]
        
        if "confidence_score" not in data:
            data["confidence_score"] = 0.85
        else:
            score = float(data["confidence_score"])
            data["confidence_score"] = max(0.70, min(0.98, score))
        
        return data