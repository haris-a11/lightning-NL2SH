import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")

SYSTEM = """You are a Linux command generator.
Return ONLY the Linux command needed to accomplish the user's task.
Never explain the command.
Never use markdown or backticks.
Never add introductory text.
If multiple commands are required, output them separated by &&."""


def generate_command(task):
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
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"/no_think\n{task}"},
                ],
                "max_tokens": 100,
                "reasoning": {"effort": "none"},
            }
        ),
    )

    return r.json()["choices"][0]["message"]["content"].strip()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python main.py <task>")

    print(generate_command(" ".join(sys.argv[1:])))
