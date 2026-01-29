from engine.nemotron import nemotron_engine
from typing import Generator
from openai.types.chat import ChatCompletionUserMessageParam, ChatCompletionSystemMessageParam


class NemotronService:
    def __init__(self):
        self._engine = nemotron_engine
    
    def _build_messages(
        self, 
        user_message: str, 
        use_reasoning: bool
    ) -> list[ChatCompletionUserMessageParam | ChatCompletionSystemMessageParam]:
        """Build messages list with optional reasoning system prompt."""
        messages: list[ChatCompletionUserMessageParam | ChatCompletionSystemMessageParam] = [
            ChatCompletionUserMessageParam(role="user", content=user_message)
        ]
        
        if use_reasoning:
            messages.insert(0, ChatCompletionSystemMessageParam(role="system", content="/think"))
        
        return messages
    
    def _build_extra_body(self, use_reasoning: bool) -> dict:
        """Build extra_body dict for reasoning tokens."""
        if use_reasoning:
            return {
                "min_thinking_tokens": 256,
                "max_thinking_tokens": 1024
            }
        return {}
    
    def generate_response(
        self, 
        user_message: str, 
        max_tokens: int = 512,
        temperature: float = 0.6,
        use_reasoning: bool = False
    ) -> str:
        """Generate a non-streaming response."""
        messages = self._build_messages(user_message, use_reasoning)
        extra_body = self._build_extra_body(use_reasoning)
        
        completion = self._engine.client.chat.completions.create(
            model=self._engine.model,
            messages=messages,
            temperature=temperature,
            top_p=0.95,
            max_tokens=max_tokens,
            stream=False,
            extra_body=extra_body
        )
        
        return completion.choices[0].message.content or ""
    
    def generate_response_stream(
        self, 
        user_message: str, 
        max_tokens: int = 512,
        temperature: float = 0.6,
        use_reasoning: bool = False
    ) -> Generator[str, None, None]:
        """Generate a streaming response."""
        messages = self._build_messages(user_message, use_reasoning)
        extra_body = self._build_extra_body(use_reasoning)
        
        completion = self._engine.client.chat.completions.create(
            model=self._engine.model,
            messages=messages,
            temperature=temperature,
            top_p=0.95,
            max_tokens=max_tokens,
            stream=True,
            extra_body=extra_body
        )
        
        for chunk in completion:
            reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
            if reasoning:
                yield reasoning
            
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content


nemotron_service = NemotronService()
