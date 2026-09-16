import os
from openai import OpenAI

api_key = os.getenv("MIMO_API_KEY")
base_url = os.getenv("MIMO_BASE_URL")
model = os.getenv("MIMO_MODEL")

print(f"BASE_URL: {base_url}")
print(f"MODEL: {model}")
print(f"KEY: {api_key[:15]}..." if api_key else "KEY: НЕТ")

client = OpenAI(api_key=api_key, base_url=base_url)

try:
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "привет"}],
        max_tokens=20,
    )
    print("ОТВЕТ:", r.choices[0].message.content)
except Exception as e:
    print(f"ОШИБКА: {type(e).__name__}: {e}")
