import openai
from typing import Dict, Any, List, Optional, Generator
import logging
import json
import asyncio
from datetime import datetime

from .llm import llm_client, LLMClient
from ..config.llm_config import llm_config

logger = logging.getLogger(__name__)

class EnhancedLLMClient(LLMClient):
    def __init__(self):
        super().__init__()
        self.conversation_history = {}
        self.tool_registry = self._initialize_tools()

    async def generate_structured_response(self, prompt: str, response_format: Dict, 
                                        context: Optional[Dict] = None) -> Dict:
        """Generate response in specific format using JSON mode"""
        try:
            system_message = """You are a CA assistant. Respond with accurate, structured JSON data.
            
            Available response formats:
            - intent_classification: {intent: string, confidence: float, entities: dict}
            - transaction_mapping: {account_code: string, confidence: float, reasoning: string}
            - compliance_advice: {deadline: string, requirements: list, penalties: list}
            - tax_calculation: {amount: float, breakdown: dict, due_date: string}
            """
            
            if context:
                system_message += f"\nContext: {json.dumps(context, indent=2)}"
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"{prompt}\n\nRespond in JSON format: {json.dumps(response_format, indent=2)}"}
            ]
            
            response = await openai.ChatCompletion.acreate(
                model=llm_config.MODEL,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Structured response generation failed: {e}")
            return self._fallback_structured_response(prompt, response_format)

    async def process_conversation(self, session_id: str, message: str, 
                                context: Optional[Dict] = None) -> Dict:
        """Process conversation with history context"""
        # Get conversation history
        history = self.conversation_history.get(session_id, [])
        
        # Prepare messages with history
        messages = []
        if context:
            messages.append({"role": "system", "content": f"Context: {json.dumps(context)}"})
        
        # Add conversation history
        for msg in history[-6:]:  # Last 6 messages for context
            messages.append(msg)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=llm_config.MODEL,
                messages=messages,
                temperature=0.7
            )
            
            assistant_response = response.choices[0].message.content
            
            # Update conversation history
            history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": assistant_response}
            ])
            self.conversation_history[session_id] = history[-10:]  # Keep last 10 messages
            
            return {
                "response": assistant_response,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Conversation processing failed: {e}")
            return {
                "response": "I apologize, I'm having trouble processing your request. Please try again.",
                "error": str(e)
            }

    async def extract_financial_entities(self, text: str) -> Dict:
        """Extract financial entities from text"""
        prompt = f"""Extract financial entities from this text:

        {text}

        Return JSON with:
        - amounts: list of monetary amounts
        - dates: list of dates
        - account_codes: list of potential account codes
        - parties: list of involved parties
        - document_types: list of document types mentioned
        - tax_references: list of tax references (GSTIN, PAN, etc.)
        """
        
        response_format = {
            "amounts": [],
            "dates": [],
            "account_codes": [],
            "parties": [],
            "document_types": [],
            "tax_references": []
        }
        
        return await self.generate_structured_response(prompt, response_format)

    async def analyze_transaction_patterns(self, transactions: List[Dict]) -> Dict:
        """Analyze transaction patterns for anomalies"""
        prompt = f"""Analyze these transactions for patterns and anomalies:

        {json.dumps(transactions, indent=2)}

        Return JSON with:
        - pattern_summary: string description
        - anomaly_flags: list of suspicious patterns
        - risk_score: number 0-100
        - recommendations: list of actions
        """
        
        response_format = {
            "pattern_summary": "",
            "anomaly_flags": [],
            "risk_score": 0,
            "recommendations": []
        }
        
        return await self.generate_structured_response(prompt, response_format)

    def _initialize_tools(self) -> Dict:
        """Initialize available tools for function calling"""
        return {
            "calculate_tax": {
                "description": "Calculate tax amounts based on income and deductions",
                "parameters": {
                    "income": {"type": "number", "description": "Taxable income"},
                    "deductions": {"type": "number", "description": "Total deductions"},
                    "financial_year": {"type": "string", "description": "Financial year"}
                }
            },
            "lookup_compliance": {
                "description": "Look up compliance requirements for a business",
                "parameters": {
                    "business_type": {"type": "string", "description": "Type of business"},
                    "turnover": {"type": "number", "description": "Annual turnover"},
                    "state": {"type": "string", "description": "Business state"}
                }
            }
        }

    def _fallback_structured_response(self, prompt: str, response_format: Dict) -> Dict:
        """Fallback response when LLM fails"""
        # Simple pattern matching fallback
        prompt_lower = prompt.lower()
        
        if 'gst' in prompt_lower:
            return {"intent": "tax_gst", "confidence": 0.8, "entities": {"tax_type": "gst"}}
        elif 'income tax' in prompt_lower:
            return {"intent": "tax_it", "confidence": 0.85, "entities": {"tax_type": "income_tax"}}
        elif 'reconcile' in prompt_lower:
            return {"intent": "reconcile", "confidence": 0.9, "entities": {}}
        else:
            return response_format  # Return empty format

# Enhanced LLM client instance
enhanced_llm = EnhancedLLMClient()