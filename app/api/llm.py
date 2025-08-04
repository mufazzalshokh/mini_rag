import os, asyncio
import openai
from openai.error import RateLimitError, APIError

openai.api_key = os.getenv("OPENAI_API_KEY")

async def stream_openai_chat_completion(
    messages,
    max_tokens: int = 400,
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.7,
    max_retries: int = 3
):
    retry = 0
    backoff = 1
    while True:
        try:
            response = await openai.ChatCompletion.acreate(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            async for chunk in response:
                yield chunk.choices[0].delta.get("content", "")
            return
        except (RateLimitError, APIError) as e:
            if retry >= max_retries:
                raise
            await asyncio.sleep(backoff)
            backoff *= 2
            retry += 1
            continue
