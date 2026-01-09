import torch
import json
from pathlib import Path
from transformers import AutoModelForVision2Seq, AutoProcessor, AutoTokenizer
from huggingface_hub import snapshot_download
from PIL import Image
import numpy as np

class QwenVLStandalone:
    def __init__(self, model_name="Qwen/Qwen3-VL-4B-Instruct", local_model_path=None):
        self.model_name = model_name
        self.local_model_path = local_model_path
        self.model = None
        self.processor = None
        self.tokenizer = None
        self.load_model()
    
    def load_model(self):
        print(f"Loading model {self.model_name}...")
        # 如果指定了本地路径，则从本地加载模型
        model_path = self.local_model_path if self.local_model_path else self.model_name
        
        self.model = AutoModelForVision2Seq.from_pretrained(
            model_path,
            device_map="auto",
            trust_remote_code=True
        ).eval()
        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        print("Model loaded successfully.")
    
    def process_image(self, image_path, prompt):
        # 加载图像
        image = Image.open(image_path)
        
        # 构建对话
        conversation = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt}
            ]
        }]
        
        # 应用模板
        text_prompt = self.processor.apply_chat_template(
            conversation, 
            tokenize=False, 
            add_generation_prompt=True
        )
        
        # 处理输入
        inputs = self.processor(
            text=text_prompt,
            images=[image],
            return_tensors="pt"
        )
        
        # 移动到设备
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        # 生成输出
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=True,
            temperature=0.6,
            top_p=0.9
        )
        
        # 解码输出
        input_ids_len = inputs["input_ids"].shape[1]
        response = self.tokenizer.decode(
            outputs[0, input_ids_len:], 
            skip_special_tokens=True
        )
        
        return response.strip()
    
    # 添加处理视频的方法
    def process_video(self, video_path, prompt, frame_count=16):
        """
        处理视频文件并生成描述
        
        Args:
            video_path (str): 视频文件路径
            prompt (str): 提示词
            frame_count (int): 采样帧数，默认16帧
            
        Returns:
            str: 视频描述结果
        """
        import cv2
        
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        # 获取视频总帧数
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 计算采样间隔
        if total_frames <= frame_count:
            indices = list(range(total_frames))
        else:
            indices = np.linspace(0, total_frames-1, frame_count, dtype=int)
        
        frames = []
        for i in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            if i in indices:
                # 转换为RGB格式并创建PIL图像
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_frame = Image.fromarray(frame_rgb)
                frames.append(pil_frame)
        
        cap.release()
        
        # 如果只有一帧，复制以满足视频处理要求
        if len(frames) == 1:
            frames.append(frames[0])
        
        # 构建对话
        conversation = [{
            "role": "user",
            "content": [
                {"type": "video", "video": frames},
                {"type": "text", "text": prompt}
            ]
        }]
        
        # 应用模板
        text_prompt = self.processor.apply_chat_template(
            conversation,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # 处理输入
        inputs = self.processor(
            text=text_prompt,
            videos=[frames],
            return_tensors="pt"
        )
        
        # 移动到设备
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        # 生成输出
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=True,
            temperature=0.6,
            top_p=0.9
        )
        
        # 解码输出
        input_ids_len = inputs["input_ids"].shape[1]
        response = self.tokenizer.decode(
            outputs[0, input_ids_len:],
            skip_special_tokens=True
        )
        
        return response.strip()

# 使用示例
if __name__ == "__main__":
    # 从HuggingFace下载并加载模型（默认方式）
    # qwen_vl = QwenVLStandalone()
    
    # 从本地路径加载模型（指定本地路径方式）
    qwen_vl = QwenVLStandalone(local_model_path=r"J:\models\LLM\Qwen-VL\Qwen3-VL-8B-Instruct")
    
    # 处理图像
    # result = qwen_vl.process_image(r"C:\Users\19864\Pictures\wan2.2chu_00051.png", "Describe this image in detail.")
    # print(result)
    
    # 处理视频 (新功能)
    result = qwen_vl.process_video(r"E:\Videos\sese10-22\标记视频片段\video_009_视频中一位穿着深蓝色裙子的女性正跪在地板上背对着镜头她的臀部微微隆起裙子的下摆遮住了她的大部分身体只.mp4", "描述视频画面。", frame_count=64)
    print(result)