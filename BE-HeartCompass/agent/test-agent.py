import requests
import json

prompt = """
请介绍下你自己
"""

url = "http://localhost:1314/api/v3/bots/chat/completions"
headers = {"Content-Type": "application/json"}
data = {
    "messages": [{"role": "user", "content": prompt}],
    "stream": True,  # 启用流式响应
}

print(f"Sending request to {url}...")
try:
    response = requests.post(url, json=data, headers=headers, stream=True)
    response.raise_for_status()

    print("Response stream:")
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode("utf-8")
            if decoded_line.startswith("data:"):
                json_str = decoded_line[5:]
                if json_str != "[DONE]":
                    delta = json.loads(decoded_line[5:])["choices"][0]["delta"][
                        "content"
                    ]
                    print(delta, end="")
except Exception as e:
    print(f"Error: {e}")
