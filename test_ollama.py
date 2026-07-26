"""Archived manual smoke test for Jimbo's original local Ollama provider."""

from ollama import Client

client = Client(host="http://127.0.0.1:11434")

response = client.chat(
    model="qwen2.5-32b-ctx32k",
    messages=[
        {"role": "user", "content": "Hello! Tell me a short joke."}
    ],
)

print(response.message.content)
