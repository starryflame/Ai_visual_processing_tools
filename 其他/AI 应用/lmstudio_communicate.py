import lmstudio as lms

with lms.Client() as client:
    model = client.llm.model("qwen/qwen3.5-35b-a3b")
    result = model.respond("你好")
    print(result)
