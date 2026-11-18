#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量动漫转写实 · 网页版（控制台 + 对比查看器）

把原桌面版与局域网查看器的全部功能集成到浏览器：选择输入/输出文件夹、
提示词与预设、全自动/半自动模式、工作流 / LoRA / 模型强度 / 步数 / CFG /
缩放 / 起始索引、开始 / 暂停 / 继续 / 停止、进度与日志、实时双图预览、
半自动确认弹窗，以及全部对比组浏览功能。

处理核心位于 anime2real_core.py（不依赖 tkinter），网页服务与前端在
tools/comfyui 下运行。参数沿用原桌面版文件格式：
    batch_anime2real_state.json   全部界面参数 + 断点（原子写入）
    prompt_presets.json           提示词预设
    viewer_state.json             上次浏览的对比图根目录

批处理任务在服务端只有一个实例，多个浏览器会共享同一个运行状态；
只读浏览互不影响，开始/暂停/停止与半自动确认会对同一个任务生效。

输出目录结构：
    output/control/<原名>             原图副本（保留原扩展名）
    output/target/<主文件名>.<扩展名>   ComfyUI 生成的图片（原样写入字节）

用法:
    python batch_anime2real_viewer.py [--port 8765] [--no-browser]
                                     [--comfy 127.0.0.1:8188]
                                     [--host 0.0.0.0] [--http-log]

从启动器启动时会保留控制台窗口：显示启动信息与批处理日志，
按 Ctrl+C 或关闭窗口即可停止服务。HTTP 轮询日志默认关闭。

平板/手机连同一 Wi-Fi 后，浏览器访问 http://<本机局域网IP>:8765
(如无法访问,请检查 Windows 防火墙是否放行 Python)

环境变量（一般用于测试或自定义部署）:
    ANIME2REAL_STATE_FILE         覆盖参数状态文件路径
    ANIME2REAL_PRESETS_FILE       覆盖提示词预设文件路径
    ANIME2REAL_VIEWER_STATE_FILE  覆盖查看器状态文件路径
    ANIME2REAL_MODELS_ROOT        覆盖模型根目录（默认 J:\\models）
    ANIME2REAL_COMFY              ComfyUI 地址（同 --comfy）
"""

import argparse
import copy
import json
import logging
import os
import socket
import string
import sys
import threading
import time
import webbrowser
from collections import deque
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_file, send_from_directory

# ComfyUI 处理器、工作流节点映射、预设/状态默认位置统一放在共享核心
# anime2real_core.py（纯处理层，不依赖 tkinter）。
from anime2real_core import (
    ComfyUIBatchProcessor,
    DEFAULT_PRESETS,
    INPUT_EXTENSIONS,
    PRESETS_FILE as CORE_PRESETS_FILE,
    STATE_FILE as CORE_STATE_FILE,
    list_input_images,
)

# ============================================================
# 常量
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
WEBUI_DIR = SCRIPT_DIR / "webui"

STATE_FILE = Path(os.environ.get("ANIME2REAL_STATE_FILE")
                  or CORE_STATE_FILE)
PRESETS_FILE = Path(os.environ.get("ANIME2REAL_PRESETS_FILE")
                    or CORE_PRESETS_FILE)
VIEWER_STATE_FILE = Path(os.environ.get("ANIME2REAL_VIEWER_STATE_FILE")
                         or (SCRIPT_DIR / "viewer_state.json"))
MODELS_ROOT = Path(os.environ.get("ANIME2REAL_MODELS_ROOT") or r"J:\models")
LORAS_ROOT = MODELS_ROOT / "loras"
CKPT_ROOT = MODELS_ROOT / "checkpoints"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
INPUT_EXTS = tuple(INPUT_EXTENSIONS)
MODES = ("全自动模式", "半自动模式")
RUNNING_EDITABLE = {"prompt", "lora", "checkpoint",
                    "strength_model", "resize_longest_edge",
                    "steps", "cfg"}
SETTINGS_KEYS = {"input_folder", "output_folder", "prompt", "workflow",
                 "lora", "checkpoint", "strength_model",
                 "resize_longest_edge", "steps", "cfg",
                 "process_mode", "start_index"}

DEFAULT_PORT = 8765
DEFAULT_PROMPT = "transform the image to realistic photograph"
SERVER_EPOCH = time.time_ns()

app = Flask(__name__, static_folder=str(WEBUI_DIR), static_url_path="/static")
try:
    app.json.ensure_ascii = False
    app.json.sort_keys = False
except AttributeError:  # 兼容旧版 Flask
    pass


# ============================================================
# 通用工具
# ============================================================

def _console_write(text):
    """把日志同步输出到控制台；无控制台或编码不支持时安全忽略。

    启动器以 CLI 方式启动时会创建独立控制台窗口，方便查看日志并用
    Ctrl+C / 关闭窗口退出。某些 Windows 控制台编码不认识 emoji，
    此时退化为 '?' 而不是让处理线程抛 UnicodeEncodeError。
    """
    stream = sys.stdout
    if stream is None:
        return
    try:
        print(text, file=stream, flush=True)
    except Exception:
        try:
            encoding = getattr(stream, "encoding", None) or "utf-8"
            safe = text.encode(encoding, "replace").decode(encoding, "replace")
            print(safe, file=stream, flush=True)
        except Exception:
            pass


def atomic_write_json(path, data):
    """原子写入 JSON：断电/崩溃时不会留下写坏的半截文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (OSError, ValueError):
        return default


def _first_workflow():
    return next(iter(ComfyUIBatchProcessor.WORKFLOW_CONFIGS))


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def default_settings():
    return {
        "input_folder": "",
        "output_folder": "",
        "prompt": DEFAULT_PROMPT,
        "workflow": _first_workflow(),
        "lora": "",
        "checkpoint": "",
        "strength_model": 1.0,
        "steps": 9,
        "cfg": 1.4,
        "resize_longest_edge": 1440,
        "process_mode": "全自动模式",
        "start_index": 0,
        "resume_file": "",
        "updated": "",
    }


def normalize_settings(data):
    """把任意来源的参数字典校验/裁剪成安全值。"""
    s = default_settings()
    if not isinstance(data, dict):
        return s

    for key in ("input_folder", "output_folder", "lora", "checkpoint"):
        value = data.get(key)
        if isinstance(value, str):
            s[key] = value.strip()
    prompt = data.get("prompt")
    if isinstance(prompt, str):
        s["prompt"] = prompt
    workflow = data.get("workflow")
    if workflow in ComfyUIBatchProcessor.WORKFLOW_CONFIGS:
        s["workflow"] = workflow
    mode = data.get("process_mode")
    if mode in MODES:
        s["process_mode"] = mode
    s["strength_model"] = round(
        min(10.0, max(0.1, _as_float(data.get("strength_model"), 1.0))), 3)
    s["steps"] = min(200, max(1, _as_int(data.get("steps"), 9)))
    s["cfg"] = round(
        min(30.0, max(0.0, _as_float(data.get("cfg"), 1.4))), 3)
    s["resize_longest_edge"] = min(
        8192, max(256, _as_int(data.get("resize_longest_edge"), 1440)))
    s["start_index"] = max(0, _as_int(data.get("start_index"), 0))
    resume_file = data.get("resume_file")
    if isinstance(resume_file, str):
        s["resume_file"] = resume_file
    return s


def _json_body():
    """只接受 JSON 请求，避免其他网页用表单跨站触发处理动作。"""
    if not request.is_json:
        return None
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def safe_file_in(base_dir, name):
    """在 base_dir 内安全解析文件，阻止目录穿越。非法/不存在返回 None。"""
    if not base_dir:
        return None
    if not name or name != os.path.basename(name) or ".." in name:
        return None
    try:
        base = Path(base_dir).resolve()
        f = (base / name).resolve()
        if os.path.commonpath([os.path.normcase(str(base)),
                               os.path.normcase(str(f))]) \
                != os.path.normcase(str(base)):
            return None
    except (OSError, ValueError):
        return None
    return f if f.is_file() else None


# ============================================================
# 参数状态（沿用原桌面版格式 batch_anime2real_state.json）
# ============================================================

class BatchStore:
    """线程安全的参数/断点存储；沿用原参数格式。"""

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.settings = self._load()

    def _load(self):
        raw = read_json(self.path, None)
        s = normalize_settings(raw if isinstance(raw, dict) else None)
        images = list_input_images(s["input_folder"])
        if images:
            # 优先按断点文件名定位，文件增删后仍能接上
            resume_file = s.get("resume_file")
            if isinstance(resume_file, str) and resume_file in images:
                s["start_index"] = images.index(resume_file)
            if s["start_index"] >= len(images):
                s["start_index"] = 0
        return s

    def _refresh_resume_locked(self):
        """根据当前 start_index 重算 resume_file（不反向修改索引）。"""
        images = list_input_images(self.settings["input_folder"])
        i = self.settings["start_index"]
        self.settings["resume_file"] = (
            images[i] if 0 <= i < len(images) else ""
        )
        return images

    def _save_locked(self):
        self._refresh_resume_locked()
        data = copy.deepcopy(self.settings)
        data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        atomic_write_json(self.path, data)

    def get(self):
        with self.lock:
            return copy.deepcopy(self.settings)

    def payload(self):
        with self.lock:
            images = list_input_images(self.settings["input_folder"])
            i = self.settings["start_index"]
            data = copy.deepcopy(self.settings)
            data["input_count"] = len(images)
            data["start_max"] = max(0, len(images) - 1)
            data["resume_file"] = images[i] if 0 <= i < len(images) else ""
            return data

    def update(self, patch, save=True):
        with self.lock:
            if isinstance(patch, dict):
                for key, value in patch.items():
                    if key in SETTINGS_KEYS:
                        self.settings[key] = value
            self.settings = normalize_settings(self.settings)
            if save:
                self._save_locked()
            return copy.deepcopy(self.settings)

    def reload(self):
        """重新读取状态文件（用于加载外部修改或手动恢复的参数）。"""
        with self.lock:
            self.settings = self._load()
            return copy.deepcopy(self.settings)


STORE = BatchStore(STATE_FILE)


# ============================================================
# 模型扫描（LoRA / Checkpoint）
# ============================================================
_MODEL_CACHE = {}
_MODEL_CACHE_LOCK = threading.Lock()
_MODEL_CACHE_TTL = 60.0


def _walk_models(folder, base, exts):
    folder = Path(folder)
    if not folder.is_dir():
        return [], f"模型文件夹不存在：{folder}"
    files = []
    try:
        for root, _dirs, names in os.walk(folder):
            for name in names:
                if Path(name).suffix.lower() in exts:
                    files.append(os.path.relpath(
                        os.path.join(root, name), str(base)))
    except OSError as e:
        return [], f"扫描模型失败：{e}"
    files.sort(key=str.lower)
    return files, ""


def scan_lora_models(workflow_name, force=False):
    cfg = ComfyUIBatchProcessor.WORKFLOW_CONFIGS.get(workflow_name) or {}
    if not cfg.get("has_lora"):
        return [], ""
    key = ("lora", workflow_name)
    now = time.time()
    with _MODEL_CACHE_LOCK:
        hit = _MODEL_CACHE.get(key)
        if hit and not force and now - hit["t"] < _MODEL_CACHE_TTL:
            return hit["files"], hit["warning"]
    folder = LORAS_ROOT / cfg.get("lora_search_subdir", "")
    files, warning = _walk_models(
        folder, LORAS_ROOT, {".safetensors", ".pt", ".pth"})
    with _MODEL_CACHE_LOCK:
        _MODEL_CACHE[key] = {"t": now, "files": files, "warning": warning}
    return files, warning


def scan_checkpoint_models(force=False):
    key = ("checkpoint", "")
    now = time.time()
    with _MODEL_CACHE_LOCK:
        hit = _MODEL_CACHE.get(key)
        if hit and not force and now - hit["t"] < _MODEL_CACHE_TTL:
            return hit["files"], hit["warning"]
    files, warning = _walk_models(
        CKPT_ROOT, CKPT_ROOT, {".safetensors", ".ckpt", ".pt"})
    with _MODEL_CACHE_LOCK:
        _MODEL_CACHE[key] = {"t": now, "files": files, "warning": warning}
    return files, warning


# ============================================================
# 提示词预设（沿用 prompt_presets.json）
# ============================================================
_PRESETS_LOCK = threading.Lock()


def load_presets():
    with _PRESETS_LOCK:
        data = read_json(PRESETS_FILE, None)
    if isinstance(data, list):
        presets = [x for x in data if isinstance(x, str) and x.strip()]
        if presets:
            return presets
    return list(DEFAULT_PRESETS)


def _save_presets(presets):
    with _PRESETS_LOCK:
        atomic_write_json(PRESETS_FILE, presets)


def update_presets(action, text):
    text = (text or "").strip()
    presets = load_presets()
    if action == "add":
        if not text:
            return False, "预设内容不能为空", presets
        if text not in presets:
            presets.append(text)
            _save_presets(presets)
        return True, "", presets
    if action == "delete":
        if text in presets:
            presets.remove(text)
            _save_presets(presets)
        return True, "", presets
    return False, "无效操作", presets


# ============================================================
# 批量处理引擎
# ============================================================

class BatchRunner:
    """在后台线程里跑批量任务，提供线程安全的快照与运行控制。"""

    def __init__(self, store, comfy_address):
        self.store = store
        self.comfy_address = comfy_address
        self.lock = threading.RLock()
        self._thread = None

        self.running = False
        self.paused = False
        self.waiting_semi = False
        self.stopping = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.semi_event = threading.Event()
        self.semi_decision = None
        self.semi_payload = None

        self.index = 0
        self.total = 0
        self.current_file = ""
        self.current_started = None
        self.success = 0
        self.fail = 0
        self.started_at = None
        self.finished_at = None
        self.last_result = None
        self.last_summary = ""
        self.completed = False

        self.input_folder = ""
        self.output_folder = ""
        self.mode = "全自动模式"
        self.processor = None

        self.logs = deque(maxlen=1000)
        self.log_seq = 0
        self._run_id = 0
        self._semi_token = 0

    # ---------- 日志与状态 ----------
    def log(self, text, kind="info"):
        now = time.time()
        with self.lock:
            self.log_seq += 1
            self.logs.append({
                "seq": self.log_seq,
                "t": now,
                "text": text,
                "kind": kind,
            })
        # 同步到启动器/终端控制台，方便直接看日志
        stamp = time.strftime("%H:%M:%S", time.localtime(now))
        _console_write(f"[{stamp}] {text}")

    def _phase_locked(self):
        if not self.running:
            return "idle"
        if self.stopping:
            return "stopping"
        if self.waiting_semi:
            return "waiting"
        if self.paused:
            return "paused"
        return "running"

    def snapshot(self, since=0):
        try:
            since = int(since)
        except (TypeError, ValueError):
            since = 0
        with self.lock:
            logs = [x for x in self.logs if x["seq"] > since]
            progress = 0.0
            if self.total:
                progress = min(self.index + 1, self.total) / self.total * 100
            semi = copy.deepcopy(self.semi_payload) \
                if self.waiting_semi else None
            return {
                "ok": True,
                "server_epoch": SERVER_EPOCH,
                "run_id": self._run_id,
                "phase": self._phase_locked(),
                "running": self.running,
                "paused": self.paused,
                "waiting_semi": self.waiting_semi,
                "stopping": self.stopping,
                "completed": self.completed,
                "comfy": self.comfy_address,
                "index": self.index,
                "total": self.total,
                "progress": progress,
                "current_file": self.current_file,
                "current_started": self.current_started,
                "success": self.success,
                "fail": self.fail,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "last_result": copy.deepcopy(self.last_result),
                "last_summary": self.last_summary,
                "semi": semi,
                "input_folder": self.input_folder,
                "output_folder": self.output_folder,
                "mode": self.mode,
                "logs": logs,
                "last_seq": self.log_seq,
            }

    # ---------- 控制 ----------
    def start(self, patch=None):
        with self.lock:
            if self.running:
                return False, "已有任务在运行，请先停止或等待完成"

        if isinstance(patch, dict):
            safe_patch = {k: v for k, v in patch.items()
                          if k in SETTINGS_KEYS}
            self.store.update(safe_patch, save=True)

        s = self.store.get()
        input_folder = s["input_folder"]
        output_folder = s["output_folder"]

        if not input_folder or not os.path.isdir(input_folder):
            return False, "请选择有效的输入文件夹"
        if not output_folder:
            return False, "请选择输出文件夹"

        images = list_input_images(input_folder)
        if not images:
            return False, "输入文件夹中没有图片（支持 .jpg / .jpeg / .png / .webp）"

        start = s["start_index"]
        if start < 0 or start >= len(images):
            return False, f"起始索引超出范围（0–{len(images) - 1}）"

        processor = ComfyUIBatchProcessor(
            server_address=self.comfy_address,
            workflow_name=s["workflow"],
        )
        if processor.has_lora_node and not s["lora"]:
            return False, "当前工作流需要 LoRA，请先选择 LoRA 模型"
        if processor.has_checkpoint and not s["checkpoint"]:
            return False, "当前工作流需要 Checkpoint，请先选择模型"

        try:
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            (Path(output_folder) / "control").mkdir(parents=True, exist_ok=True)
            (Path(output_folder) / "target").mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return False, f"无法创建输出目录：{e}"

        preflight_warning = ""
        try:
            requests.get(f"http://{self.comfy_address}/system_stats",
                         timeout=2)
        except requests.RequestException:
            preflight_warning = (
                f"⚠ 无法连接 ComfyUI（{self.comfy_address}），"
                "任务仍会启动，处理时会自动重试"
            )

        with self.lock:
            if self.running:
                return False, "已有任务在运行"

            self.running = True
            self.paused = False
            self.waiting_semi = False
            self.stopping = False
            self.stop_event.clear()
            self.pause_event.set()
            self.semi_event.clear()
            self.semi_decision = None
            self.semi_payload = None

            self.processor = processor
            self.input_folder = input_folder
            self.output_folder = output_folder
            self.mode = s["process_mode"]
            self.index = start
            self.total = len(images)
            self.success = 0
            self.fail = 0
            self.current_file = images[start]
            self.current_started = None
            self.started_at = time.time()
            self.finished_at = None
            self.last_result = None
            self.last_summary = ""
            self.completed = False
            self._run_id += 1
            self._semi_token = 0

            self.log("─" * 20 + " 新的处理任务 " + "─" * 20)
            self.log(f"▶ 开始处理：共 {len(images)} 张，从索引 {start} 开始"
                     f"（{s['process_mode']}）")
            self.log(f"   输入：{input_folder}")
            self.log(f"   输出：{output_folder}")
            self.log(f"   工作流：{s['workflow']} · 步数 {s['steps']} · "
                     f"CFG {s['cfg']} · 缩放最长边 "
                     f"{s['resize_longest_edge']}px")
            if processor.has_lora_node:
                self.log(f"   LoRA：{s['lora']} · 强度 "
                         f"{s['strength_model']}")
            if preflight_warning:
                self.log(preflight_warning, "warn")

            self._thread = threading.Thread(
                target=self._run,
                args=(dict(s), images, start, processor),
                daemon=True,
                name="a2r-batch",
            )
            self._thread.start()
        return True, ""

    def pause(self):
        with self.lock:
            if not self.running:
                return False, "当前没有任务在运行"
            if self.paused:
                return False, "已经是暂停状态"
            self.paused = True
            self.pause_event.clear()
            if self.waiting_semi:
                self.log("⏸ 已请求暂停：确认后将在下一张开始前暂停", "warn")
            else:
                self.log("⏸ 已暂停：当前图片完成后生效", "warn")
        return True, ""

    def resume(self):
        with self.lock:
            if not self.running:
                return False, "当前没有任务在运行"
            if not self.paused:
                return False, "当前不是暂停状态"
            self.paused = False
            self.pause_event.set()
            self.log("▶ 已继续", "info")
        return True, ""

    def stop(self):
        with self.lock:
            if not self.running:
                return False, "当前没有任务在运行"
            if self.stopping:
                return True, ""
            self.stopping = True
            self.stop_event.set()
            self.pause_event.set()
            if self.waiting_semi:
                self.semi_event.set()
            self.log("⏹ 正在停止…（等待当前 ComfyUI 请求结束）", "warn")
        return True, ""

    def decide(self, action, prompt=None):
        if action not in ("next", "retry", "stop"):
            return False, "无效操作"
        with self.lock:
            if not self.waiting_semi:
                return False, "当前不在等待确认状态"
            if self.semi_decision is not None:
                return False, "决定已提交，正在继续…"

            if isinstance(prompt, str):
                current = self.store.get().get("prompt", "")
                if prompt != current:
                    self.store.update({"prompt": prompt}, save=True)
                    self.log("✏ 提示词已更新（用于本次重试/后续图片）", "info")

            self.semi_decision = action
            if action == "stop":
                self.stopping = True
                self.stop_event.set()
            self.semi_event.set()
        return True, ""

    # ---------- 半自动确认 ----------
    def _wait_semi(self, next_index, images):
        next_file = images[next_index] if next_index < len(images) else ""
        after_file = (images[next_index + 1]
                      if next_index + 1 < len(images) else "")
        next_mtime = None
        if next_file:
            try:
                next_mtime = os.stat(
                    os.path.join(self.input_folder, next_file)).st_mtime
            except OSError:
                pass
        prompt = self.store.get().get("prompt", "")

        with self.lock:
            self._semi_token += 1
            self.waiting_semi = True
            self.semi_decision = None
            self.semi_payload = {
                "token": f"{self._run_id}:{self._semi_token}",
                "prompt": prompt,
                "next_file": next_file,
                "after_file": after_file,
                "next_mtime": next_mtime,
                "next_index": next_index,
                "total": len(images),
                "last_result": copy.deepcopy(self.last_result),
            }
            self.semi_event.clear()
            self.log("⏸ 等待人工确认（重新生成 / 下一张 / 停止）", "warn")

        decision = "stop"
        while True:
            if self.stop_event.is_set():
                decision = "stop"
                break
            if self.semi_event.wait(0.2):
                with self.lock:
                    decision = self.semi_decision or "stop"
                break

        with self.lock:
            self.waiting_semi = False
            self.semi_decision = None
            if self.stop_event.is_set():
                decision = "stop"

        if decision == "next":
            self.log("✓ 已确认，继续下一张", "ok")
        elif decision == "retry":
            self.log("↻ 重新生成当前图片…", "warn")
        else:
            self.log("⏹ 停止", "warn")
        return decision

    # ---------- 主循环 ----------
    def _record_result(self, filename, ok, result):
        data = {
            "input_name": filename,
            "ok": bool(ok),
            "message": str(result),
            "ts": time.time(),
        }
        if ok:
            path = Path(result)
            data["output_name"] = path.name
            data["output_path"] = str(path)
            try:
                data["output_mtime"] = path.stat().st_mtime
            except OSError:
                data["output_mtime"] = None
            control_path = Path(self.output_folder) / "control" / filename
            if control_path.is_file():
                data["control_name"] = filename
                try:
                    data["control_mtime"] = control_path.stat().st_mtime
                except OSError:
                    data["control_mtime"] = None
        with self.lock:
            self.last_result = data

    def _save_progress(self, index):
        try:
            self.store.update({"start_index": index}, save=True)
        except OSError as e:
            self.log(f"⚠ 保存断点失败：{e}", "warn")

    def _run(self, settings, images, start, processor):
        total = len(images)
        i = start
        reason = "done"

        try:
            while i < total:
                if self.stop_event.is_set():
                    reason = "stopped"
                    break

                # 暂停点：图片之间才生效
                while not self.pause_event.is_set():
                    if self.stop_event.wait(0.2):
                        break
                if self.stop_event.is_set():
                    reason = "stopped"
                    break

                live = self.store.get()
                prompt = (live.get("prompt") or "").strip()
                lora = live.get("lora", "") if processor.has_lora_node else None
                checkpoint = (live.get("checkpoint", "")
                              if processor.has_checkpoint else None)
                strength = live.get("strength_model", 1.0)
                steps = live.get("steps", 9)
                cfg_value = live.get("cfg", 1.4)
                resize = live.get("resize_longest_edge", 1440)

                filename = images[i]
                input_path = os.path.join(self.input_folder, filename)
                with self.lock:
                    self.index = i
                    self.current_file = filename
                    self.current_started = time.time()

                # 断点先落盘：处理这张时若断电，下次启动会从这张重新开始
                self._save_progress(i)
                self.log(f"[{i + 1}/{total}] 处理 {filename}", "info")

                ok, result = False, ""
                try:
                    workflow = processor.load_workflow()
                    ok, result = processor.process_image(
                        workflow,
                        input_path,
                        self.output_folder,
                        os.path.join(self.output_folder, "control"),
                        os.path.join(self.output_folder, "target"),
                        prompt,
                        lora,
                        strength,
                        checkpoint,
                        resize,
                        steps_value=steps,
                        cfg_value=cfg_value,
                        stop_check=self.stop_event.is_set,
                    )
                except Exception as e:  # 单张异常不拖垮整个批次
                    ok, result = False, f"处理异常：{e}"

                if self.stop_event.is_set():
                    with self.lock:
                        self.current_started = None
                        if ok:
                            # 停止请求发出时这张刚好生成完成，仍计入成功
                            self.success += 1
                    self._record_result(filename, ok, result)
                    if ok:
                        self.log(f"✓ {filename} → {Path(result).name}"
                                 "（停止前已完成）", "ok")
                    else:
                        self.log("⏹ 处理已停止", "warn")
                    reason = "stopped"
                    break

                if ok:
                    with self.lock:
                        self.success += 1
                        self.current_started = None
                    self._record_result(filename, True, result)
                    self.log(f"✓ {filename} → {Path(result).name}", "ok")
                else:
                    with self.lock:
                        self.fail += 1
                        self.current_started = None
                    self._record_result(filename, False, result)
                    self.log(f"✗ {filename} - {result}", "err")

                if self.mode == "半自动模式":
                    decision = self._wait_semi(i + 1, images)
                    if decision == "stop":
                        reason = "stopped"
                        break
                    if decision == "retry":
                        continue
                    i += 1
                else:
                    i += 1
        except Exception as e:
            self.log(f"✗ 批次异常终止：{e}", "err")
            reason = "error"
        finally:
            self._finish(i, total, reason)

    def _finish(self, i, total, reason):
        resumed_at = 0
        if i < total:
            resumed_at = max(0, min(i, total - 1))

        try:
            self.store.update({"start_index": resumed_at}, save=True)
        except OSError as e:
            self.log(f"⚠ 保存断点失败：{e}", "warn")

        finished_normally = (i >= total) and reason != "error"
        with self.lock:
            self.running = False
            self.paused = False
            self.waiting_semi = False
            self.stopping = False
            self.current_started = None
            self.finished_at = time.time()
            self.completed = finished_normally
            self.semi_payload = None
            if self.total:
                self.index = min(self.index, self.total - 1)
            self.pause_event.set()
            self.last_summary = (
                f"成功 {self.success} · 失败 {self.fail} · "
                f"共 {self.total} 张"
            )

        if finished_normally:
            self.log(f"🎉 处理完成：{self.last_summary}", "ok")
        elif reason == "error":
            self.log(f"✗ 批次异常结束：{self.last_summary}", "err")
        else:
            self.log(
                f"⏹ 已停止：{self.last_summary}；"
                f"下次将从第 {resumed_at + 1} 张（索引 {resumed_at}）继续",
                "warn",
            )


RUNNER = BatchRunner(
    STORE,
    os.environ.get("ANIME2REAL_COMFY") or "127.0.0.1:8188",
)

_COMFY_STATUS_LOCK = threading.Lock()
_COMFY_STATUS = {"t": 0.0, "data": None}


# ============================================================
# 对比组扫描（沿用原查看器逻辑）
# ============================================================

def scan_pairs(job_path):
    """按主文件名配对 control/ 与 target/ 中的图片，按最新在前排序。"""
    job_path = Path(job_path)
    control_dir = job_path / "control"
    target_dir = job_path / "target"

    cinfo, tinfo = {}, {}
    for d, info in ((control_dir, cinfo), (target_dir, tinfo)):
        if d.is_dir():
            try:
                for p in d.iterdir():
                    if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                        info.setdefault(p.stem, p)
            except OSError:
                pass

    all_stems = set(cinfo) | set(tinfo)
    pairs = []
    for stem in all_stems:
        c, t = cinfo.get(stem), tinfo.get(stem)
        try:
            c_m = c.stat().st_mtime if c else None
            t_m = t.stat().st_mtime if t else None
        except OSError:
            continue
        max_m = max(x for x in (c_m, t_m) if x is not None)
        pairs.append({
            "name": stem,
            "control_name": c.name if c else None,
            "target_name": t.name if t else None,
            "has_control": c is not None,
            "has_target": t is not None,
            "control_mtime": c_m,
            "target_mtime": t_m,
            "max_mtime": max_m,
        })
    pairs.sort(key=lambda p: p["max_mtime"], reverse=True)
    return pairs


def safe_image_file(job, side, name):
    """解析对比图路径，并阻止目录穿越。"""
    if side not in ("control", "target"):
        return None
    if not job:
        return None
    return safe_file_in(Path(job) / side, name)


# ============================================================
# 局域网 IP / 查看器状态
# ============================================================

def get_lan_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ips)


def load_viewer_settings():
    data = read_json(VIEWER_STATE_FILE, {})
    if not isinstance(data, dict):
        data = {}
    return {
        "root": data.get("root", "") if isinstance(data.get("root"), str) else "",
        "job": data.get("job", "") if isinstance(data.get("job"), str) else "",
        "manual": bool(data.get("manual", False)),
    }


def save_viewer_settings(root, job, manual=True):
    try:
        atomic_write_json(VIEWER_STATE_FILE, {
            "root": root,
            "job": job,
            "manual": manual,
        })
        return True
    except OSError:
        return False


def detect_output_folder():
    """当前输出文件夹，用于查看器自动定位。"""
    out = (STORE.get().get("output_folder") or "").strip()
    if not out:
        return ""
    p = Path(out)
    return str(p) if p.is_dir() else ""


def resolve_viewer_settings():
    cur = load_viewer_settings()
    auto = detect_output_folder()
    if auto and (not cur["manual"] or not Path(cur["root"]).is_dir()):
        return {"root": auto, "job": auto, "manual": False, "detected": auto}
    return {
        "root": cur["root"],
        "job": cur["job"],
        "manual": cur["manual"],
        "detected": auto,
    }


# ============================================================
# 路由：页面与静态资源
# ============================================================

@app.route("/")
def index():
    if not (WEBUI_DIR / "index.html").is_file():
        return ("前端资源缺失：请确认 tools/comfyui/webui/index.html 存在",
                500)
    resp = send_from_directory(WEBUI_DIR, "index.html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


# ============================================================
# 路由：网页版配置 / 参数 / 模型 / 预设
# ============================================================

@app.route("/api/config")
def api_config():
    reload_requested = request.args.get("reload") == "1"
    if reload_requested and not RUNNER.running:
        STORE.reload()

    workflows = []
    loras = {}
    lora_warnings = {}
    for name, cfg in ComfyUIBatchProcessor.WORKFLOW_CONFIGS.items():
        workflows.append({
            "name": name,
            "has_lora": bool(cfg.get("has_lora")),
            "has_checkpoint": bool(cfg.get("has_checkpoint")),
            "has_steps": bool(cfg.get("steps_node")),
            "steps_node": cfg.get("steps_node", ""),
            "has_cfg": bool(cfg.get("cfg_node")),
            "cfg_node": cfg.get("cfg_node", ""),
            "lora_default": cfg.get("lora_default", ""),
            "lora_search_subdir": cfg.get("lora_search_subdir", ""),
        })
        if cfg.get("has_lora"):
            files, warning = scan_lora_models(
                name, force=reload_requested)
            loras[name] = files
            if warning:
                lora_warnings[name] = warning

    checkpoints, ckpt_warning = scan_checkpoint_models(
        force=reload_requested)

    return jsonify(
        ok=True,
        comfy=RUNNER.comfy_address,
        server_epoch=SERVER_EPOCH,
        workflows=workflows,
        default_workflow=_first_workflow(),
        loras=loras,
        lora_warnings=lora_warnings,
        checkpoints=checkpoints,
        checkpoint_warning=ckpt_warning,
        checkpoint_default=r"Qwen-Image-Edit-Remix-AIO-v2.0.safetensors",
        presets=load_presets(),
        settings=STORE.payload(),
        viewer=resolve_viewer_settings(),
        modes=list(MODES),
        input_exts=list(INPUT_EXTS),
        models_root=str(MODELS_ROOT),
    )


@app.route("/api/batch-settings", methods=["GET", "POST"])
def api_batch_settings():
    if request.method == "GET":
        return jsonify(ok=True, settings=STORE.payload())
    data = _json_body()
    if data is None:
        return jsonify(ok=False, error="需要 JSON 请求"), 415
    patch = {k: v for k, v in data.items() if k in SETTINGS_KEYS}
    ignored = []
    if RUNNER.running:
        ignored = [k for k in patch if k not in RUNNING_EDITABLE]
        patch = {k: v for k, v in patch.items() if k in RUNNING_EDITABLE}
    try:
        STORE.update(patch, save=True)
    except OSError as e:
        return jsonify(ok=False, error=f"保存参数失败：{e}",
                       settings=STORE.payload())
    return jsonify(ok=True, ignored=ignored, settings=STORE.payload())


@app.route("/api/models")
def api_models():
    kind = request.args.get("kind", "")
    force = request.args.get("force") == "1"
    if kind == "lora":
        workflow = request.args.get("workflow", "")
        files, warning = scan_lora_models(workflow, force=force)
        return jsonify(ok=True, kind="lora", workflow=workflow,
                       files=files, warning=warning)
    if kind == "checkpoint":
        files, warning = scan_checkpoint_models(force=force)
        return jsonify(ok=True, kind="checkpoint",
                       files=files, warning=warning)
    return jsonify(ok=False, error="未知的模型类型")


@app.route("/api/presets", methods=["POST"])
def api_presets():
    data = _json_body()
    if data is None:
        return jsonify(ok=False, error="需要 JSON 请求"), 415
    ok, error, presets = update_presets(
        data.get("action", ""), data.get("text", ""))
    return jsonify(ok=ok, error=error, presets=presets)


@app.route("/api/input-list")
def api_input_list():
    folder = request.args.get("folder", "")
    if not folder:
        return jsonify(ok=True, folder="", count=0,
                       first="", last="", exists=False)
    if not Path(folder).is_dir():
        return jsonify(ok=False, error="目录不存在", count=0)
    images = list_input_images(folder)
    return jsonify(
        ok=True,
        folder=folder,
        exists=True,
        count=len(images),
        first=images[0] if images else "",
        last=images[-1] if images else "",
    )


# ============================================================
# 路由：运行控制 / 状态 / 输入图片
# ============================================================

@app.route("/api/run/start", methods=["POST"])
def api_run_start():
    data = _json_body()
    if data is None:
        return jsonify(ok=False, error="需要 JSON 请求"), 415
    patch = data.get("settings") if isinstance(data.get("settings"), dict) else None
    ok, error = RUNNER.start(patch)
    return jsonify(ok=ok, error=error,
                   phase="running" if ok else "idle")


@app.route("/api/run/pause", methods=["POST"])
def api_run_pause():
    if _json_body() is None:
        return jsonify(ok=False, error="需要 JSON 请求"), 415
    ok, error = RUNNER.pause()
    return jsonify(ok=ok, error=error)


@app.route("/api/run/resume", methods=["POST"])
def api_run_resume():
    if _json_body() is None:
        return jsonify(ok=False, error="需要 JSON 请求"), 415
    ok, error = RUNNER.resume()
    return jsonify(ok=ok, error=error)


@app.route("/api/run/stop", methods=["POST"])
def api_run_stop():
    if _json_body() is None:
        return jsonify(ok=False, error="需要 JSON 请求"), 415
    ok, error = RUNNER.stop()
    return jsonify(ok=ok, error=error)


@app.route("/api/semi", methods=["POST"])
def api_semi():
    data = _json_body()
    if data is None:
        return jsonify(ok=False, error="需要 JSON 请求"), 415
    ok, error = RUNNER.decide(data.get("action", ""),
                              data.get("prompt"))
    return jsonify(ok=ok, error=error)


@app.route("/api/status")
def api_status():
    return jsonify(RUNNER.snapshot(request.args.get("since", 0)))


@app.route("/api/comfy-status")
def api_comfy_status():
    now = time.time()
    with _COMFY_STATUS_LOCK:
        if _COMFY_STATUS["data"] and now - _COMFY_STATUS["t"] < 4:
            return jsonify(_COMFY_STATUS["data"])
    try:
        r = requests.get(f"http://{RUNNER.comfy_address}/system_stats",
                         timeout=2)
        data = {"ok": bool(r.ok), "address": RUNNER.comfy_address,
                "error": "" if r.ok else f"HTTP {r.status_code}"}
    except requests.RequestException as e:
        data = {"ok": False, "address": RUNNER.comfy_address,
                "error": str(e)}
    with _COMFY_STATUS_LOCK:
        _COMFY_STATUS["t"] = now
        _COMFY_STATUS["data"] = data
    return jsonify(data)


@app.route("/api/input-image")
def api_input_image():
    name = request.args.get("name", "")
    folder = STORE.get().get("input_folder", "")
    f = safe_file_in(folder, name)
    if f is None:
        return "Not Found", 404
    return send_file(f, conditional=True, max_age=0)


# ============================================================
# 路由：对比查看器（保留原查看器全部 API）
# ============================================================

@app.route("/api/settings")
def api_settings():
    return jsonify(ok=True, **resolve_viewer_settings())


@app.route("/api/save", methods=["POST"])
def api_save():
    data = _json_body()
    if data is None:
        return jsonify(ok=False, error="需要 JSON 请求"), 415
    root = data.get("root", "")
    job = data.get("job", "")
    manual = bool(data.get("manual", True))
    return jsonify(ok=save_viewer_settings(root, job, manual))


@app.route("/api/autodetect")
def api_autodetect():
    auto = detect_output_folder()
    if not auto:
        return jsonify(
            ok=False,
            error="未找到输出文件夹记录（请先选择输出文件夹）",
        )
    return jsonify(ok=True, root=auto, job=auto)


@app.route("/api/dirs")
def api_dirs():
    p = request.args.get("path", "")
    if not p:
        drives = [f"{d}:\\" for d in string.ascii_uppercase
                  if os.path.exists(f"{d}:\\")]
        return jsonify(ok=True, path="", parent=None, entries=drives,
                       drive=True)

    path = Path(p)
    if not path.is_dir():
        return jsonify(ok=False, error="目录不存在")

    try:
        entries = sorted(
            (e.name for e in path.iterdir()
             if e.is_dir() and not e.name.startswith((".", "$"))),
            key=str.lower,
        )
    except OSError:
        entries = []
    parent = str(path.parent) if path.parent != path else None
    return jsonify(ok=True, path=str(path), parent=parent,
                   entries=entries, drive=False)


@app.route("/api/jobs")
def api_jobs():
    root = request.args.get("root", "")
    rp = Path(root)
    jobs = []

    def qualifies(d):
        return (d / "control").is_dir() or (d / "target").is_dir()

    if rp.is_dir():
        if qualifies(rp):
            jobs.append(str(rp))
        try:
            subdirs = sorted((e for e in rp.iterdir() if e.is_dir()),
                             key=lambda e: e.name.lower())
        except OSError:
            subdirs = []
        for sub in subdirs:
            if qualifies(sub):
                jobs.append(str(sub))
        if not jobs:
            jobs.append(str(rp))
    return jsonify(ok=True, root=root, jobs=jobs)


@app.route("/api/state")
def api_state():
    root = request.args.get("root", "")
    job = request.args.get("job", "")
    jp = Path(job) if job else Path(root)
    if not jp.is_dir():
        return jsonify(ok=True, root=root, job=job, exists=False,
                       count=0, latest=None)
    pairs = scan_pairs(jp)
    return jsonify(ok=True, root=root, job=job, exists=True,
                   count=len(pairs),
                   latest=pairs[0] if pairs else None)


@app.route("/api/pairs")
def api_pairs():
    job = request.args.get("job", "")
    jp = Path(job)
    if not jp.is_dir():
        return jsonify(ok=True, job=job, pairs=[])
    return jsonify(ok=True, job=job, pairs=scan_pairs(jp))


@app.route("/api/image")
def api_image():
    job = request.args.get("job", "")
    side = request.args.get("side", "")
    name = request.args.get("name", "")
    f = safe_image_file(job, side, name)
    if f is None:
        return "Not Found", 404
    return send_file(f, conditional=True, max_age=0)


# ============================================================
# 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="批量动漫转写实 · 网页版控制台与对比查看器")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"监听端口（默认 {DEFAULT_PORT}）")
    parser.add_argument("--host", default="0.0.0.0",
                        help="监听地址（默认 0.0.0.0，局域网可访问）")
    parser.add_argument("--comfy",
                        default=os.environ.get("ANIME2REAL_COMFY")
                        or "127.0.0.1:8188",
                        help="ComfyUI 地址，host:port（默认 127.0.0.1:8188）")
    parser.add_argument("--no-browser", action="store_true",
                        help="启动时不自动打开浏览器")
    parser.add_argument("--http-log", action="store_true",
                        help="输出每个 HTTP 请求日志（默认关闭，避免浏览器轮询刷屏）")
    args = parser.parse_args()

    RUNNER.comfy_address = args.comfy

    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(
                "批量动漫转写实 · 网页控制台")
        except Exception:
            pass

    # 浏览器会每秒轮询状态，默认关闭 Werkzeug 的请求日志，
    # 只保留启动信息与批处理日志；需要排查 HTTP 时加 --http-log。
    if not args.http_log:
        logging.getLogger("werkzeug").setLevel(logging.WARNING)

    ips = get_lan_ips()
    print("=" * 60)
    print("批量动漫转写实 · 网页版控制台已启动")
    print(f"本机访问:   http://127.0.0.1:{args.port}")
    if ips:
        for ip in ips:
            print(f"局域网访问: http://{ip}:{args.port}")
        print("平板/手机需与电脑连同一 Wi-Fi，在浏览器打开上面地址即可")
    print(f"ComfyUI:    http://{args.comfy}")
    print(f"参数状态:   {STATE_FILE}")
    print(f"提示词预设: {PRESETS_FILE}")
    print("日志输出到本窗口；按 Ctrl+C 或直接关闭窗口即可停止服务")
    print("(HTTP 轮询日志默认关闭，需要时加 --http-log)")
    print("(如无法访问,请检查 Windows 防火墙是否放行 Python)")
    print("=" * 60)

    if not args.no_browser:
        threading.Timer(
            1.0, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")
        ).start()

    try:
        app.run(host=args.host, port=args.port, threaded=True, debug=False)
    except KeyboardInterrupt:
        _console_write("\n⏹ 已停止网页服务；若任务中断，下次启动会从断点继续")
    except OSError:
        message = (f"端口 {args.port} 被占用，请换一个端口重试："
                   f"--port 其他端口")
        print(message)
        # 控制台可能被重定向或无控制台，再用弹窗兜底
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("启动失败", message)
            root.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
