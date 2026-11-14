"""一次模型请求；只接收调用方提供的 messages，不隐式保存会话。"""


def ask_model(client, model, messages, options):
    response = client.chat.completions.create(model=model, messages=messages, **options)
    if not response.choices:
        raise ValueError("模型没有返回候选回答。")
    if response.choices[0].finish_reason == "length":
        raise ValueError("模型输出达到 token 上限，请检查输出预算。")
    text = response.choices[0].message.content
    if not text or not text.strip():
        raise ValueError("模型未返回文字。")
    return text.strip()
