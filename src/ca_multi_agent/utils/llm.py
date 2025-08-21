import openai
from typing import Dict, Any, List, Optional
import logging
from ..config.llm_config import llm_config

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.configured = False
        self.configure()
    
    def configure(self):
        """Configure LLM client with settings"""
        try:
            if llm_config.API_KEY:
                openai.api_key = llm_config.API_KEY
                if llm_config.BASE_URL:
                    openai.api_base = llm_config.BASE_URL
                self.configured = True
                logger.info("LLM client configured successfully")
            else:
                logger.warning("No LLM API key configured. Using mock responses.")
        except Exception as e:
            logger.error(f"LLM configuration failed: {e}")
    
    async def generate_response(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Generate response using LLM"""
        if not self.configured:
            return self._mock_llm_response(prompt)
        
        try:
            messages = self._prepare_messages(prompt, context)
            
            response = await openai.ChatCompletion.acreate(
                model=llm_config.MODEL,
                messages=messages,
                temperature=llm_config.TEMPERATURE,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return self._mock_llm_response(prompt)
    
    def _prepare_messages(self, prompt: str, context: Optional[Dict]) -> List[Dict]:
        """Prepare messages for LLM API"""
        messages = []
        
        # System message with context
        system_message = "You are a helpful CA assistant specializing in Indian accounting and taxation."
        if context:
            system_message += f" Context: {context}"
        messages.append({"role": "system", "content": system_message})
        
        # User message
        messages.append({"role": "user", "content": prompt})
        
        return messages
    
    def _mock_llm_response(self, prompt: str) -> str:
        """Mock LLM response for development"""
        prompt_lower = prompt.lower()
        
        if 'gst' in prompt_lower:
            return "Based on your query about GST, I recommend filing GSTR-1 by the 11th of next month and GSTR-3B by the 20th. Make sure to reconcile your input tax credit with GSTR-2B."
        elif 'income tax' in prompt_lower:
            return "For income tax, please ensure you pay advance tax installments by the due dates to avoid interest penalties. The due dates are typically June 15, September 15, December 15, and March 15."
        elif 'tds' in prompt_lower:
            return "TDS should be deducted at the time of payment or credit, whichever is earlier. File TDS returns using Form 24Q for salaries and Form 26Q for non-salaries by the due dates."
        elif 'compliance' in prompt_lower:
            return "Key compliance deadlines: GST returns monthly, TDS returns quarterly, and annual financial statements by September 30th for companies."
        else:
            return "I understand you're asking about accounting and taxation. Could you please provide more specific details so I can assist you better?"

    async def extract_entities(self, text: str, entity_types: List[str]) -> Dict[str, Any]:
        """Extract specific entities from text using LLM"""
        if not self.configured:
            return self._mock_entity_extraction(text, entity_types)
        
        prompt = f"Extract the following entities from this text: {', '.join(entity_types)}\n\nText: {text}\n\nReturn as JSON:"
        
        try:
            response = await self.generate_response(prompt)
            # Parse JSON response
            import json
            return json.loads(response)
        except:
            return self._mock_entity_extraction(text, entity_types)
    
    def _mock_entity_extraction(self, text: str, entity_types: List[str]) -> Dict:
        """Mock entity extraction for development"""
        result = {}
        for entity_type in entity_types:
            if entity_type == 'amount':
                result['amount'] = ['₹10,000', '₹5,000']
            elif entity_type == 'date':
                result['date'] = ['2024-03-15', '2024-03-31']
            elif entity_type == 'gstin':
                result['gstin'] = ['27ABCDE1234F1Z5']
            elif entity_type == 'pan':
                result['pan'] = ['ABCDE1234F']
        return result

# Global LLM client instance
llm_client = LLMClient()