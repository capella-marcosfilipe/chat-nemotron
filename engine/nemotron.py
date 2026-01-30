# engine/nemotron.py
"""
Nemotron engine with automatic GPU/API fallback.
"""
import torch
from typing import Literal
from openai import OpenAI
import os
from transformers import AutoModelForCausalLM, AutoTokenizer

EngineMode = Literal["gpu", "api"]


class NemotronEngine:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Constructor for singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Nemotron engine with GPU/API fallback."""
        if NemotronEngine._initialized:
            return
        
        # Detect CUDA availability
        self._cuda_available: bool = torch.cuda.is_available()
        
        # Initialize API client (always available)
        self._api_client: OpenAI = self._init_api_client()
        
        # Initialize GPU model if CUDA is available
        self._gpu_model = None
        self._gpu_tokenizer = None
        if self._cuda_available:
            try:
                self._gpu_model, self._gpu_tokenizer = self._init_gpu_model()
                print("✓ GPU model loaded successfully!")
            except Exception as e:
                print(f"✗ Failed to load GPU model: {e}")
                self._cuda_available = False
        
        NemotronEngine._initialized = True
    
    def _init_api_client(self) -> OpenAI:
        """Initialize NVIDIA API client."""
        print("Initializing NVIDIA API client...")
        api_key = os.getenv(
            "NVIDIA_API_KEY",
            "your_default_api_key_here"
        )
        return OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
    
    def _init_gpu_model(self):
        """Initialize local GPU model."""
        
        
        print("Loading Nemotron GPU model...")
        tokenizer = AutoTokenizer.from_pretrained("nvidia/NVIDIA-Nemotron-Nano-9B-v2")
        
        model = AutoModelForCausalLM.from_pretrained(
            "nvidia/NVIDIA-Nemotron-Nano-9B-v2",
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map="auto"
        )
        
        return model, tokenizer
    
    @property
    def cuda_available(self) -> bool:
        """Check if CUDA is available and model is loaded."""
        return self._cuda_available and self._gpu_model is not None
    
    @property
    def api_client(self) -> OpenAI:
        """Get API client."""
        return self._api_client
    
    @property
    def gpu_model(self):
        """Get GPU model (raises if not available)."""
        if not self.cuda_available:
            raise RuntimeError("GPU model not available")
        return self._gpu_model
    
    @property
    def gpu_tokenizer(self):
        """Get GPU tokenizer (raises if not available)."""
        if not self.cuda_available:
            raise RuntimeError("GPU tokenizer not available")
        return self._gpu_tokenizer
    
    @property
    def default_mode(self) -> EngineMode:
        """Get default mode based on CUDA availability."""
        return "gpu" if self.cuda_available else "api"


# Singleton instance
nemotron_engine = NemotronEngine()
