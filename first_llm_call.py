# Please install OpenAI SDK first: `pip3 install openai`

import os
from openai import OpenAI

# client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1")
client = OpenAI(api_key=os.getenv("DASHSCOPE_API_KEY"), base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")


response = client.chat.completions.create(
    model="deepseek-v3",
    messages=[
        {"role": "system", "content": "你在回答博士生的提问。"},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hello! 👋 How can I assist you today? 😊"},
        {"role": "user", "content": "你好，我是张三，我想咨询一下关于深度求索的问题。"}
    ],
    stream=False
)

message = response.choices[0].message
print(message.content)

