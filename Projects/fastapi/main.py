from fastapi import FastAPI
from openai import OpenAI

client = OpenAI(
    api_key="", base_url="https://api.deepseek.com"
)


app = FastAPI()

history = [{"role": "system", "content": "你是一个助手"}]


@app.post("/chat")
async def chat(query: str):
    history.append({"role": "user", "content": query})
    response = client.chat.completions.create(
        model="deepseek-v4-flash",  # 或 deepseek-v4-flash
        messages=history,
    )

    history.append({"role": "assistant", "content": response.choices[0].message.content})
    print(history)

    return {"response": response}


@app.post("/stream")
async def stream(query: str):
    history.append({"role": "user", "content": query})
    response = client.chat.completions.create(
        model="deepseek-v4-flash",  # 或 deepseek-v4-flash
        messages=history,
        stream=True,
    )

    content = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            print(text, end="")
            content += text

    history.append({"role": "assistant", "content": content})

    return {"response": content}