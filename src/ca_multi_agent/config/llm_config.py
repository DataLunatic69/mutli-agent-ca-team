from src.ca_multi_agent.config.settings import settings

class LLMConfig:
    # TODO: Add actual LLM configuration
    PROVIDER = "openai"  # or "anthropic", "ollama", etc.
    MODEL = "gpt-3.5-turbo"
    API_KEY = None
    BASE_URL = None
    TEMPERATURE = 0.1
    
    @classmethod
    def setup(cls):
        # This will be populated from environment variables
        cls.API_KEY = settings.LLM_API_KEY if hasattr(settings, 'LLM_API_KEY') else None
        cls.BASE_URL = settings.LLM_BASE_URL if hasattr(settings, 'LLM_BASE_URL') else None

llm_config = LLMConfig()