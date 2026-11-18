#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI 批量动漫转写实 · 共享处理核心

从原 Tkinter 桌面版中抽出的纯处理层，不依赖 tkinter / PIL。
网页版（batch_anime2real_viewer.py）直接复用这里的处理器、工作流节点映射、
状态/预设默认路径和输入图片扫描逻辑。

工作流输出约定：
    output/control/<原名>             原图副本（保留原扩展名）
    output/target/<主文件名>.<扩展名>   ComfyUI 生成的图片（原样写入字节）
"""

import json
import os
import random
import time
from pathlib import Path

import requests


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKFLOWS_DIR = os.path.join(SCRIPT_DIR, "工作流")
STATE_FILE = os.path.join(SCRIPT_DIR, "batch_anime2real_state.json")
PRESETS_FILE = os.path.join(SCRIPT_DIR, "prompt_presets.json")
INPUT_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

DEFAULT_PRESETS = [
    "transform the image to realistic photograph",
    "动漫转真人",
    "动漫转写实",
    "写实转二次元动漫风格",
]


def list_input_images(folder):
    """按稳定顺序列出输入图片。

    排序规则与旧版桌面工具一致（直接 sorted），保证历史断点索引
    仍然指向同一张图。
    """
    if not folder:
        return []
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    out = []
    for name in names:
        if Path(name).suffix.lower() not in INPUT_EXTENSIONS:
            continue
        if (Path(folder) / name).is_file():
            out.append(name)
    return sorted(out)


class ComfyUIBatchProcessor:
    """ComfyUI 批量处理器"""

    # 工作流配置：定义每个工作流的节点 ID 映射
    WORKFLOW_CONFIGS = {
        "Qwen2.1_漫转写实真人": {
            # Qwen Image 2.1 图像编辑工作流，LoRA 仅扫描 J:\models\loras\qwenimage2.1
            "file": "image_qwen_image_2_1_image_edit.json",
            "load_image_node": "470",
            "prompt_node": "493",
            "resize_node": "480",
            "seed_node": "489",
            "steps_node": "489",
            "cfg_node": "489",
            "has_lora": True,
            "lora_node": "498",
            "lora_search_subdir": r"qwenimage2.1",
            "lora_default": r"qwenimage2.1\anime2real4_c1-st5000.safetensors",
        },
        "Qwen2.1_无LoRA": {
            # 与上一条同一工作流，但去掉了 LoRA 节点（494），直接用底模
            "file": "image_qwen_image_2_1_image_edit_no_lora.json",
            "load_image_node": "470",
            "prompt_node": "493",
            "resize_node": "480",
            "seed_node": "489",
            "steps_node": "489",
            "cfg_node": "489",
            "has_lora": False,
            "has_checkpoint": False,
        },
    }

    def __init__(self, server_address="127.0.0.1:8188", workflow_name=None):
        self.server_address = server_address
        # 名字对不上（改名/删掉旧工作流）时退回第一个，避免整个界面启动就崩
        if workflow_name not in self.WORKFLOW_CONFIGS:
            workflow_name = next(iter(self.WORKFLOW_CONFIGS))
        self.workflow_name = workflow_name
        self.config = self.WORKFLOW_CONFIGS[workflow_name]
        self.workflow_path = os.path.join(
            WORKFLOWS_DIR, self.config["file"])

    @property
    def has_lora_node(self):
        """当前工作流是否包含自定义 LoRA 节点"""
        return self.config.get("has_lora", False)

    @property
    def has_checkpoint(self):
        """当前工作流是否需要选择 Checkpoint 模型"""
        return self.config.get("has_checkpoint", False)

    def load_workflow(self):
        """加载工作流配置"""
        with open(self.workflow_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def queue_prompt(self, prompt):
        """提交任务到 ComfyUI"""
        url = f"http://{self.server_address}/prompt"
        data = {"prompt": prompt}
        response = requests.post(url, json=data, timeout=10)
        return response.json()

    def get_history(self, prompt_id):
        """获取任务历史"""
        url = f"http://{self.server_address}/history/{prompt_id}"
        response = requests.get(url, timeout=10)
        return response.json()

    def get_image(self, filename, subfolder, folder_type):
        """获取生成的图片"""
        params = {"filename": filename, "subfolder": subfolder,
                  "type": folder_type}
        url = f"http://{self.server_address}/view"
        response = requests.get(url, params=params, timeout=30)
        return response.content

    @staticmethod
    def _remove_stale_outputs(folder, stem, keep_name):
        """删除同一张图之前生成的、扩展名不对的旧输出。

        旧版本会用输入图的扩展名命名（例如输入 .jpg 时把 ComfyUI 的 PNG
        存成了 .jpg），重新生成后会在 target 里留下同名的旧文件。
        只删除确实是图片格式（PNG/JPEG/WEBP）的文件，避免误删其他文件。
        """
        try:
            names = os.listdir(folder)
        except OSError:
            return
        for name in names:
            if name == keep_name:
                continue
            p = Path(name)
            if p.stem != stem or p.suffix.lower() not in (
                    ".png", ".jpg", ".jpeg", ".webp"):
                continue
            path = os.path.join(folder, name)
            try:
                with open(path, "rb") as fh:
                    head = fh.read(12)
                is_image = (
                    head.startswith(b"\x89PNG\r\n\x1a\n")
                    or head.startswith(b"\xff\xd8\xff")
                    or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")
                )
                if is_image:
                    os.remove(path)
            except OSError:
                continue

    def upload_image(self, image_path):
        """上传图片到 ComfyUI input 目录，返回文件名"""
        url = f"http://{self.server_address}/upload/image"
        with open(image_path, 'rb') as f:
            files = {'image': (os.path.basename(image_path), f, 'image/png')}
            response = requests.post(url, files=files, timeout=30)
        data = response.json()
        name = data["name"]
        subfolder = data.get("subfolder", "")
        if subfolder:
            return os.path.join(subfolder, name)
        return name

    def process_image(self, workflow, input_image_path, output_folder,
                      original_folder, output_image_folder, prompt,
                      lora_name=None, strength_model=1.5,
                      checkpoint_name=None, resize_longest_edge=1440,
                      steps_value=9, cfg_value=1.4, stop_check=None):
        """处理单张图片。stop_check 是可选的 callable，返回 True 时应中止处理。"""
        cfg = self.config

        # 上传图片到 ComfyUI input 目录，获取文件名
        try:
            image_filename = self.upload_image(input_image_path)
        except requests.exceptions.RequestException:
            return False, "ComfyUI 连接失败（上传图片时无法连接到服务器）"
        except Exception:
            return False, "上传图片失败"

        # 修改 LoadImage 节点的输入图片
        workflow[cfg["load_image_node"]]["inputs"]["image"] = image_filename

        # 修改提示词（仅当工作流配置了提示词节点）
        prompt_node = cfg.get("prompt_node")
        if prompt_node and prompt_node in workflow:
            workflow[prompt_node]["inputs"]["prompt"] = prompt

        # 修改 LoRA（仅限有 LoRA 的工作流）
        if cfg.get("has_lora"):
            lora_node = cfg["lora_node"]
            if lora_node in workflow:
                # 普通 LoraLoader 节点用 lora_name/strength_model，
                # rgthree LoRA堆加载器用 lora_01/strength_01，可通过配置指定
                name_key = cfg.get("lora_name_input", "lora_name")
                strength_key = cfg.get("lora_strength_input", "strength_model")
                workflow[lora_node]["inputs"][name_key] = lora_name
                workflow[lora_node]["inputs"][strength_key] = strength_model

        # 修改 Checkpoint（仅限有 checkpoint 的工作流）
        if cfg.get("has_checkpoint") and checkpoint_name:
            ckpt_node = cfg["checkpoint_node"]
            if ckpt_node in workflow:
                workflow[ckpt_node]["inputs"]["ckpt_name"] = checkpoint_name

        # 修改缩放最长边长度（仅当工作流配置了缩放节点）
        resize_node = cfg.get("resize_node")
        if resize_node and resize_node in workflow:
            workflow[resize_node]["inputs"]["scale_to_length"] = resize_longest_edge

        # 随机化采样种子（仅当工作流配置了种子节点）
        seed_node = cfg.get("seed_node")
        if seed_node and seed_node in workflow and "seed" in workflow[seed_node]["inputs"]:
            max_seed = 1125899906842624  # rgthree Seed 节点的上限，约 2^50，足够随机
            workflow[seed_node]["inputs"]["seed"] = random.randint(0, max_seed)

        # 修改采样参数：步数 / CFG（当前工作流的 KSampler 节点为 489）
        steps_node = cfg.get("steps_node")
        if steps_node and steps_node in workflow:
            node_inputs = workflow[steps_node].get("inputs")
            if node_inputs is not None and "steps" in node_inputs:
                try:
                    node_inputs["steps"] = max(1, int(steps_value))
                except (TypeError, ValueError):
                    pass
        cfg_node = cfg.get("cfg_node")
        if cfg_node and cfg_node in workflow:
            node_inputs = workflow[cfg_node].get("inputs")
            if node_inputs is not None and "cfg" in node_inputs:
                try:
                    node_inputs["cfg"] = float(cfg_value)
                except (TypeError, ValueError):
                    pass

        # 提交任务
        try:
            result = self.queue_prompt(workflow)
        except requests.exceptions.RequestException:
            return False, "ComfyUI 连接失败（提交任务时无法连接到服务器）"

        if "prompt_id" not in result:
            return False, "任务提交失败"

        prompt_id = result["prompt_id"]

        # 等待任务完成
        max_wait = 300  # 最大等待 5 分钟
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if stop_check and stop_check():
                return False, "用户停止"

            # 使用较短的超时，让停止检查能及时生效
            try:
                history = self.get_history(prompt_id)
            except requests.exceptions.RequestException:
                time.sleep(2)
                continue

            if prompt_id in history:
                outputs = history[prompt_id]["outputs"]
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        for img in node_output["images"]:
                            try:
                                img_data = self.get_image(
                                    img["filename"],
                                    img.get("subfolder", ""),
                                    img.get("type", "output"),
                                )
                            except requests.exceptions.RequestException:
                                return False, "ComfyUI 连接失败（获取图片时无法连接到服务器）"
                            # 输出文件必须和 ComfyUI 生成的文件完全一致（原样写入字节），
                            # 否则 PNG 里的 prompt/workflow 元数据会丢失。
                            # 扩展名要跟随 ComfyUI 返回的文件名，而不是输入图的扩展名：
                            # 输入是 .jpg 时 ComfyUI 输出仍然是 PNG，若命名为 .jpg，
                            # 拖回 ComfyUI 时前端按 image/jpeg 处理，读不到 PNG 元数据。
                            comfy_ext = Path(img.get("filename", "")).suffix.lower()
                            if comfy_ext not in (".png", ".jpg", ".jpeg", ".webp"):
                                comfy_ext = ".png"
                            output_name = f"{Path(input_image_path).stem}{comfy_ext}"
                            output_path = os.path.join(
                                output_image_folder, output_name)
                            self._remove_stale_outputs(
                                output_image_folder,
                                Path(input_image_path).stem,
                                output_name,
                            )
                            with open(output_path, 'wb') as f:
                                f.write(img_data)
                            # 复制原图到原图文件夹 - 保持相同文件名和格式
                            original_path = os.path.join(
                                original_folder,
                                Path(input_image_path).name,
                            )
                            with open(input_image_path, 'rb') as src:
                                with open(original_path, 'wb') as dst:
                                    dst.write(src.read())
                            return True, output_path
            time.sleep(1)

        return False, "任务超时"
