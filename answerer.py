import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"

conversation_history = []

def generate_answer(question, context_chunks):
    if not context_chunks:
        return "I don't have enough information in the notes to answer this."

    context = "\n\n".join([f"[{c['source']}]: {c['text']}" for c in context_chunks])

    system_prompt = """You are a strict study assistant.
1. ONLY use the provided NOTES.
2. If the answer is not in the notes, say exactly: I don't have enough information in the notes to answer this.
3. Always cite your source as Page X, Section Y.
4. Never make up information."""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"NOTES:\n{context}\n\nQUESTION: {question}"}
        ],
        "stream": False,
        "options": {"temperature": 0}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        answer = response.json()["message"]["content"]
        conversation_history.append({"q": question, "a": answer})
        return answer
    except Exception as e:
        return f"Error: Ensure Ollama is running. {str(e)}"