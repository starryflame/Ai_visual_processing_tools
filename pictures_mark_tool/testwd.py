import onnxruntime as ort
from PIL import Image
import numpy as np
import csv
import os

# --- 1. 定义 ONNX 模型路径 ---
model_onnx_path = r"J:\lora-scripts-v1.12.0\huggingface\hub\models--SmilingWolf--wd-vit-tagger-v3\snapshots\7f6b584d0bd3f55c4531f14ba3d4761b2bccdc0f\model.onnx"

# --- 2. 加载 ONNX Runtime 会话 ---
# providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] # 如果安装了 onnxruntime-gpu
providers = ['CPUExecutionProvider']
ort_session = ort.InferenceSession(model_onnx_path, providers=providers)

# --- 3. 加载标签信息 ---
tags_path = r"J:\lora-scripts-v1.12.0\huggingface\hub\models--SmilingWolf--wd-vit-tagger-v3\snapshots\7f6b584d0bd3f55c4531f14ba3d4761b2bccdc0f\selected_tags.csv"

tags = []
try:
    with open(tags_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader) # 跳过标题行
        tags = [row[1] for row in reader]
    print(f"成功从 {tags_path} 加载了 {len(tags)} 个标签。")
except FileNotFoundError:
    print(f"警告：未找到标签文件 {tags_path}。")
    tags = None


# --- 4. 定义正确的图像预处理函数 (关键修改在这里) ---
def preprocess_image(image_path, size=(448, 448)):
    """
    加载并预处理图像，使其符合 ONNX 模型的要求。
    此模型期望 NHWC 格式的输入: (Batch, Height, Width, Channels)
    """
    image = Image.open(image_path).convert("RGB") # 确保是 RGB
    image = image.resize(size, Image.BICUBIC) # 调整大小到 448x448
    
    # 转换为 numpy 数组 (H, W, C) - 这已经是 NHWC 中的 HWC 部分
    image_np = np.array(image, dtype=np.float32)
    
    # 归一化到 [0, 1] (根据模型要求，有些模型可能需要 [-1, 1] 或 ImageNet 标准化)
    image_np /= 255.0
    
    # 添加批次维度 (H, W, C) -> (1, H, W, C)
    # 这就得到了最终的 NHWC 格式 (1, 448, 448, 3)
    image_input = np.expand_dims(image_np, axis=0)
    
    return image_input # 返回形状为 (1, 448, 448, 3)


# --- 5. 准备输入图像 ---
image_path = r"J:\ai-toolkit\datasets\ほうき星 (2021.09.05 - 2025.05.11) - 副本\0001_9802830_2_202551_Y0H0RTOrjFsChiySE3zyVvt2.png" # <--- 替换成你的测试图片路径
input_tensor = preprocess_image(image_path)
print(f"输入张量形状: {input_tensor.shape}") # 应该打印 (1, 448, 448, 3)

# --- 6. 执行推理 ---
input_name = ort_session.get_inputs()[0].name
print(f"ONNX 模型输入名称: {input_name}")

outputs = ort_session.run(None, {input_name: input_tensor})
logits = outputs[0]
print(f"Logits 形状: {logits.shape}") # 应该是 (1, N) N是标签数

# --- 7. 处理输出 ---
probs = 1 / (1 + np.exp(-logits[0])) # Sigmoid

# 获取图片的基本名称（不含扩展名）
image_basename = os.path.splitext(os.path.basename(image_path))[0]
txt_output_path = os.path.join(os.path.dirname(image_path), f"{image_basename}.txt")

if tags is not None and len(tags) == len(probs):
    results = list(zip(tags, probs))
    sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
    top_n = 10
    print(f"\nTop {top_n} tags for {os.path.basename(image_path)}:")
    for tag, prob in sorted_results[:top_n]:
        print(f"{tag}: {prob:.4f}")
    
    # 将结果写入txt文件
    with open(txt_output_path, 'w', encoding='utf-8') as f:
        for tag, prob in sorted_results[:top_n]:
            f.write(f"{tag}\n")
    print(f"\n标签已保存到: {txt_output_path}")
else:
    print("\n标签加载失败或数量不匹配，仅显示前10个原始概率值:")
    for i, p in enumerate(probs[:10]):
        print(f"Output_{i}: {p:.4f}")
    
    # 即使标签加载失败，也将原始概率值写入txt文件
    with open(txt_output_path, 'w', encoding='utf-8') as f:
        for i, p in enumerate(probs[:10]):
            f.write(f"Output_{i}\n")
    print(f"\n原始概率值已保存到: {txt_output_path}")