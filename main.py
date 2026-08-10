import requests
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
# task = input("Enter your task: ")

# take the task from the command line argument if provided
if len(sys.argv) > 1:
    task = " ".join(sys.argv[1:])

r = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    },
    data=json.dumps(
        {
            "model": "qwen/qwen3-14b",
            "messages": [
                {
                    "role": "system",
                    "content": """You are a Linux command generator.
Return ONLY the Linux command needed to accomplish the user's task.
Never explain the command.
Never use markdown or backticks.
Never add introductory text.
If multiple commands are required, output them separated by &&.""",
                },
                {
                    "role": "user",
                    "content": f"/no_think\n{task}",
                },
            ],
            "max_tokens": 50,
            "reasoning": {"effort": "none"},
        }
    ),
)


data = r.json()

print(data["choices"][0]["message"]["content"].strip())
