import os
from openai import OpenAI

client = OpenAI(
  api_key=os.getenv("DASHSCOPE_API_KEY"),
  base_url="https://maas.qianwenaiapi.com/compatible-mode/v1",
)

while True:
    user_input = input("你:")

    response = client.chat.completions.create(
    model="qwen3.8-max",
    messages=[{
        "role": "user",
        "content": user_input
        }
    ]
    )
    print(response)
    print(response.choices[0].message.content)