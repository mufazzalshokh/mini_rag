from time import perf_counter
from typing import List, Dict
from .vectorstore import similarity_search_with_citations
from .llm import stream_openai_chat_completion
from .token_utils import estimate_costs


async def run_rag_chain(question: str, max_tokens: int, budget_usd: float):
    start_time = perf_counter()

    # Step 1: Hybrid retrieval
    relevant_chunks = similarity_search_with_citations(question, k=5)

    # Build context
    context = "\n\n".join([chunk['content'] for chunk in relevant_chunks])

    # Step 2: Create prompt
    prompt = f"""Answer the question using the provided context. Be concise and accurate.

Context:
{context}

Question: {question}
Answer:"""

    # Step 3: Stream answer from OpenAI
    async_gen, token_counter = stream_openai_chat_completion(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.2
    )

    # Yield token stream (caller handles SSE)
    async for token in async_gen:
        yield {"type": "token", "content": token}

        # Budget check
        cost = estimate_costs(token_counter["prompt"] + token_counter["completion"])
        if cost > budget_usd:
            yield {
                "type": "done",
                "content": {
                    "answer": "[aborted due to budget limit]",
                    "citations": [],
                    "usage": {
                        "prompt_tokens": token_counter["prompt"],
                        "completion_tokens": token_counter["completion"],
                        "cost_usd": cost,
                        "latency_ms": int((perf_counter() - start_time) * 1000)
                    }
                }
            }
            return

    # Step 4: After finish, return citations and usage
    final_answer = token_counter["answer"]
    citations = [{
        "source_id": f"{chunk['source']}#{chunk['page']}",
        "snippet": chunk['content'][:200]
    } for chunk in relevant_chunks]

    yield {
        "type": "done",
        "content": {
            "answer": final_answer,
            "citations": citations,
            "usage": {
                "prompt_tokens": token_counter["prompt"],
                "completion_tokens": token_counter["completion"],
                "cost_usd": estimate_costs(token_counter["prompt"] + token_counter["completion"]),
                "latency_ms": int((perf_counter() - start_time) * 1000)
            }
        }
    }
