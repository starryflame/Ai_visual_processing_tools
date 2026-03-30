import lmstudio as lms

with lms.Client() as client:
    model = client.llm.model("qwen/qwen3.5-35b-a3b")
    
    # 流式输出模式 - respond_stream 用于聊天响应
    for fragment in model.respond_stream("你好"):
        print(fragment.content, end="", flush=True)
