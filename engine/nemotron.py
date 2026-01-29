"""
Singleton class for Nemotron API client.
Uses OpenAI-compatible NVIDIA API.
"""
from openai import OpenAI
import os


class NemotronEngine:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if NemotronEngine._initialized:
            return
            
        print("Initializing NVIDIA Nemotron API client...")
        
        api_key = os.getenv("NVIDIA_API_KEY", "")
        
        self._client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        
        self._model = "nvidia/nvidia-nemotron-nano-9b-v2"
        
        print("NVIDIA Nemotron API client initialized!")
        NemotronEngine._initialized = True
    
    @property
    def client(self) -> OpenAI:
        """Get the OpenAI client instance."""
        return self._client
    
    @property
    def model(self) -> str:
        """Get the model name."""
        return self._model


# Singleton instance
nemotron_engine = NemotronEngine()
