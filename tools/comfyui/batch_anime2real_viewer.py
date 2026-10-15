#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动漫转写实 · 网页实时双图查看器

在局域网内通过浏览器实时查看桌面版「批量动漫转写实」处理中的
原图 / 生成图 对比。处理流程仍由桌面版 GUI (batch_anime2real.py) 控制,
本服务被动监控输出文件夹,自动展示最新一组对比图。

桌面版输出目录结构:
    output_folder/control/<原名>  原图副本
    output_folder/target/<原名>   生成图副本(同名同扩展名)
本工具按「文件名相同」配对两侧图片。

输出目录会自动识别:桌面版每次选择/开始处理时会把输出文件夹写入
batch_anime2real_state.json,本服务启动即读取它并自动跳转到该目录,
之后处理中途切换输出文件夹也会自动跟随。也可用「🔍 自动检测」按钮手动触发。

用法:
    python batch_anime2real_viewer.py [--port 8765] [--no-browser]

平板/手机连同一 Wi-Fi 后,浏览器访问 http://<本机局域网IP>:8765 即可。
(如无法访问,请检查 Windows 防火墙是否放行 Python)
"""

import argparse
import json
import os
import socket
import string
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, request, send_file

# ============================================================
# 常量
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
STATE_FILE = SCRIPT_DIR / "viewer_state.json"   # 记住上次选择的 root/job
DESKTOP_STATE_FILE = SCRIPT_DIR / "batch_anime2real_state.json"  # 桌面版记录的输出文件夹,用于自动定位
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
DEFAULT_PORT = 8765

app = Flask(__name__)

# ============================================================
# 核心逻辑:扫描对比组
# ============================================================

def scan_pairs(job_path):
    """扫描任务文件夹,按文件名配对 control/ 与 target/ 中的图片。

    返回按 max(两侧 mtime) 从新到旧排序的列表:
        [{name, has_control, has_target, control_mtime, target_mtime, max_mtime}, ...]
    """
    control_dir = job_path / "control"
    target_dir = job_path / "target"

    # 收集两侧文件信息
    cinfo, tinfo = {}, {}
    for d, info in ((control_dir, cinfo), (target_dir, tinfo)):
        if d.is_dir():
            for p in d.iterdir():
                if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                    info[p.name] = p

    all_names = set(cinfo) | set(tinfo)
    pairs = []
    for name in all_names:
        c, t = cinfo.get(name), tinfo.get(name)
        c_m = c.stat().st_mtime if c else None
        t_m = t.stat().st_mtime if t else None
        max_m = max(x for x in (c_m, t_m) if x is not None)
        pairs.append({
            "name": name,
            "has_control": c is not None,
            "has_target": t is not None,
            "control_mtime": c_m,
            "target_mtime": t_m,
            "max_mtime": max_m,
        })
    pairs.sort(key=lambda p: p["max_mtime"], reverse=True)
    return pairs


def safe_image_file(job, side, name):
    """校验并解析图片路径,防止目录穿越。非法时返回 None。"""
    if side not in ("control", "target"):
        return None
    if not name or name != os.path.basename(name) or ".." in name:
        return None
    job_p = Path(job).resolve()
    base = (job_p / side).resolve()
    f = (base / name).resolve()
    try:
        if os.path.commonpath([os.path.normcase(str(base)), os.path.normcase(str(f))]) != os.path.normcase(str(base)):
            return None
    except ValueError:
        return None
    if not f.is_file():
        return None
    return f

# ============================================================
# 局域网 IP
# ============================================================

def get_lan_ips():
    """获取本机局域网 IPv4 地址列表"""
    ips = set()
    try:
        # UDP 连接不实际发包,仅用于获取本机出口 IP
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

# ============================================================
# 状态持久化
# ============================================================

def load_settings():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "root": data.get("root", ""),
                "job": data.get("job", ""),
                "manual": bool(data.get("manual", False)),
            }
    except (OSError, ValueError):
        return {"root": "", "job": "", "manual": False}


def save_settings(root, job, manual=True):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"root": root, "job": job, "manual": manual},
                      f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def detect_desktop_output():
    """读取桌面版(batch_anime2real.py)记录的输出文件夹。

    返回该目录的绝对路径字符串;未记录、路径为空或目录已不存在时返回 ""。
    """
    try:
        with open(DESKTOP_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return ""
    out = str(data.get("output_folder") or "").strip()
    if not out:
        return ""
    p = Path(out)
    return str(p) if p.is_dir() else ""


def resolve_settings():
    """决定查看器使用的 root/job。

    默认跟随桌面版记录的输出文件夹;若用户在查看器里手动选过目录
    (manual 为真)且该目录仍然存在,则以手动选择为准。
    """
    cur = load_settings()
    auto = detect_desktop_output()
    if auto and (not cur["manual"] or not Path(cur["root"]).is_dir()):
        return {"root": auto, "job": auto, "manual": False, "detected": auto}
    return {"root": cur["root"], "job": cur["job"],
            "manual": cur["manual"], "detected": auto}

# ============================================================
# API 路由
# ============================================================

@app.route("/")
def index():
    return PAGE_HTML


@app.route("/api/settings")
def api_settings():
    return jsonify(ok=True, **resolve_settings())


@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.get_json(silent=True) or {}
    root = data.get("root", "")
    job = data.get("job", "")
    manual = bool(data.get("manual", True))
    return jsonify(ok=save_settings(root, job, manual))


@app.route("/api/autodetect")
def api_autodetect():
    """重新读取桌面版记录的输出文件夹,供「自动检测」按钮与轮询使用。"""
    auto = detect_desktop_output()
    if not auto:
        return jsonify(ok=False, error="未找到 batch_anime2real.py 的输出文件夹记录"
                                       "(桌面版尚未选择或开始处理过)")
    return jsonify(ok=True, root=auto, job=auto)


@app.route("/api/dirs")
def api_dirs():
    """目录浏览。path 为空时返回磁盘列表。"""
    p = request.args.get("path", "")
    if not p:
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        return jsonify(ok=True, path="", parent=None, entries=drives, drive=True)

    path = Path(p)
    if not path.is_dir():
        return jsonify(ok=False, error="目录不存在")

    entries = []
    try:
        entries = sorted(
            (e.name for e in path.iterdir() if e.is_dir()
             and not e.name.startswith((".", "$"))),
            key=str.lower,
        )
    except OSError:
        pass
    parent = str(path.parent) if path.parent != path else None
    return jsonify(ok=True, path=str(path), parent=parent, entries=entries, drive=False)


@app.route("/api/jobs")
def api_jobs():
    """扫描 root 下所有「任务文件夹」(包含 control/ 或 target/ 子目录的目录)。"""
    root = request.args.get("root", "")
    rp = Path(root)
    jobs = []

    def qualifies(d):
        return (d / "control").is_dir() or (d / "target").is_dir()

    if rp.is_dir():
        if qualifies(rp):
            jobs.append(str(rp))
        try:
            subdirs = sorted((e for e in rp.iterdir() if e.is_dir()), key=lambda e: e.name.lower())
        except OSError:
            subdirs = []
        for sub in subdirs:
            if qualifies(sub):
                jobs.append(str(sub))
        # 输出文件夹刚选定、还没生成 control/target 时,仍列出根目录,
        # 这样查看器能一直等待并自动显示第一组结果
        if not jobs:
            jobs.append(str(rp))
    return jsonify(ok=True, root=root, jobs=jobs)


@app.route("/api/state")
def api_state():
    """轻量轮询接口:对比组总数 + 最新一组。"""
    root = request.args.get("root", "")
    job = request.args.get("job", "")
    jp = Path(job) if job else Path(root)

    if not jp.is_dir():
        return jsonify(ok=True, root=root, job=job, exists=False, count=0, latest=None)

    pairs = scan_pairs(jp)
    return jsonify(
        ok=True, root=root, job=job, exists=True,
        count=len(pairs), latest=pairs[0] if pairs else None,
    )


@app.route("/api/pairs")
def api_pairs():
    """完整对比组列表(手动浏览时按需拉取,不包含图片数据)。"""
    job = request.args.get("job", "")
    jp = Path(job)
    if not jp.is_dir():
        return jsonify(ok=True, job=job, pairs=[])
    return jsonify(ok=True, job=job, pairs=scan_pairs(jp))


@app.route("/api/image")
def api_image():
    """按需发送图片。参数: job / side(control|target) / name / t(缓存戳)"""
    job = request.args.get("job", "")
    side = request.args.get("side", "")
    name = request.args.get("name", "")
    f = safe_image_file(job, side, name)
    if f is None:
        return "Not Found", 404
    return send_file(f, conditional=True, max_age=0)

# ============================================================
# 前端页面(内嵌 HTML)
# ============================================================

PAGE_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%232196F3'/><rect x='5' y='7' width='9' height='18' rx='2' fill='%23fff'/><rect x='18' y='7' width='9' height='18' rx='2' fill='%234CAF50'/></svg>">
<title>动漫转写实 · 实时双图查看器</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
html, body { height:100%; }
body {
    background:#141414; color:#e8e8e8;
    font-family:"Microsoft YaHei UI","PingFang SC",system-ui,sans-serif;
    display:flex; flex-direction:column;
}
header {
    background:#1d1d1d; padding:10px 16px; border-bottom:1px solid #2c2c2c;
    display:flex; flex-wrap:wrap; align-items:center; gap:10px;
}
.title { font-size:18px; font-weight:bold; color:#fff; margin-right:6px; }
.controls { display:flex; flex-wrap:wrap; align-items:center; gap:8px; }
button {
    background:#2a2a2a; color:#e8e8e8; border:1px solid #3d3d3d;
    border-radius:6px; padding:6px 12px; cursor:pointer; font-size:13px;
}
button:hover { background:#3a3a3a; }
select {
    background:#1d1d1d; color:#e8e8e8; border:1px solid #3d3d3d;
    border-radius:6px; padding:6px 8px; font-size:13px; max-width:340px;
}
#root-path { color:#8ab4f8; font-size:12px; word-break:break-all; }
label.chk { display:flex; align-items:center; gap:5px; font-size:13px; color:#ccc; cursor:pointer; }
.status { width:100%; color:#9aa0a6; font-size:12px; min-height:16px; }
main { flex:1; display:flex; gap:0; padding:10px; min-height:0; position:relative; }
.panel {
    flex:1; display:flex; flex-direction:column; min-width:0;
    background:#1a1a1a; border:1px solid #2c2c2c; border-radius:10px; overflow:hidden;
}
/* 横屏:两面板在中缝处无缝贴合(同原桌面版),去掉中间缝隙 */
@media (min-width: 769px) {
    .panel.input  { border-right:none; border-top-right-radius:0; border-bottom-right-radius:0; }
    .panel.output { border-left:none;  border-top-left-radius:0;  border-bottom-left-radius:0; }
}
/* 上一对 / 下一对 导航按钮(左右边缘,垂直居中) */
.nav-btn {
    position:absolute; top:50%; transform:translateY(-50%); z-index:30;
    width:42px; height:42px; border-radius:50%;
    background:rgba(28,28,28,.9); color:#ddd; border:1px solid #444;
    font-size:15px; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
}
.nav-btn:hover:not(:disabled) { background:#3a3a3a; color:#fff; border-color:#6a6a6a; }
.nav-btn:disabled { opacity:.3; cursor:default; }
#btn-prev { left:2px; }
#btn-next { right:2px; }
.panel-title { padding:10px; font-weight:bold; font-size:15px; text-align:center; }
.panel.input .panel-title { color:#2196F3; }
.panel.output .panel-title { color:#4CAF50; }
.imgwrap {
    flex:1; display:flex; align-items:center; justify-content:center;
    min-height:0; background:#0f0f0f;
}
.imgwrap img { max-width:100%; max-height:100%; object-fit:contain; }
/* 双图紧贴中缝(同原桌面版:输入图靠右、输出图靠左) */
.panel.input .imgwrap img { margin-left:auto; }
.panel.output .imgwrap img { margin-right:auto; }
.placeholder { color:#666; font-size:14px; text-align:center; padding:10px; }
.panel-meta {
    padding:8px 10px; font-size:12px; color:#9aa0a6; text-align:center;
    border-top:1px solid #262626;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
@keyframes glow {
    0%   { box-shadow:0 0 0 rgba(255,215,0,0); }
    30%  { box-shadow:0 0 46px rgba(255,215,0,.55); }
    100% { box-shadow:0 0 0 rgba(255,215,0,0); }
}
.flash { animation: glow 1s ease-out; }
.hidden { display:none !important; }

/* 对比组抽屉 */
#drawer {
    position:fixed; top:0; right:0; bottom:0; width:min(430px, 92vw);
    background:#1d1d1d; border-left:1px solid #2c2c2c; z-index:50;
    transform:translateX(105%); transition:transform .25s ease;
    display:flex; flex-direction:column;
}
#drawer.open { transform:translateX(0); }
#drawer-head { display:flex; justify-content:space-between; align-items:center; padding:12px 14px; border-bottom:1px solid #2c2c2c; }
#drawer-head b { font-size:15px; }
#pair-list { flex:1; overflow-y:auto; padding:8px; }
.pair-item {
    display:flex; gap:8px; align-items:center; padding:8px;
    border:1px solid #2c2c2c; border-radius:8px; background:#242424;
    cursor:pointer; margin-bottom:8px;
}
.pair-item:hover { background:#2d3240; border-color:#4a6fa5; }
.pair-item img { width:64px; height:64px; object-fit:cover; border-radius:4px; background:#111; }
.pair-info { flex:1; min-width:0; }
.pair-name { font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.pair-time { font-size:10px; color:#888; margin-top:3px; }
.chips { margin-top:4px; }
.chips span { display:inline-block; font-size:10px; padding:1px 7px; border-radius:8px; margin-right:4px; }
.chip-ok  { background:#1b5e20; color:#a5d6a7; }
.chip-miss{ background:#4e342e; color:#ffab91; }

/* 目录选择弹窗 */
#modal {
    position:fixed; inset:0; background:rgba(0,0,0,.6); z-index:60;
    display:flex; align-items:center; justify-content:center;
}
#modal-card {
    width:min(540px, 94vw); max-height:82vh; background:#1d1d1d;
    border:1px solid #333; border-radius:12px; overflow:hidden;
    display:flex; flex-direction:column;
}
#modal-head { padding:12px 14px; border-bottom:1px solid #2c2c2c; display:flex; justify-content:space-between; align-items:center; }
#modal-head b { font-size:15px; }
#modal-path { padding:8px 14px; color:#8ab4f8; font-size:12px; word-break:break-all; border-bottom:1px solid #222; }
#dir-list { flex:1; overflow-y:auto; padding:6px 10px; }
.dir-item { padding:8px 10px; border-radius:6px; cursor:pointer; font-size:14px; }
.dir-item:hover { background:#2a2a2a; }
.dir-item.drive { color:#ffd54f; font-weight:bold; }
.dir-empty { padding:20px; text-align:center; color:#666; font-size:13px; }
#modal-foot { padding:10px 14px; border-top:1px solid #2c2c2c; display:flex; justify-content:flex-end; gap:8px; }

@media (max-width: 768px) {
    main { flex-direction:column; gap:10px; }
    .panel { min-height:0; }
    /* 竖屏时面板上下排列,没有中缝,恢复居中 */
    .panel.input .imgwrap img { margin-left:0; }
    .panel.output .imgwrap img { margin-right:0; }
}
</style>
</head>
<body>
<header>
    <div class="title">🎨 动漫转写实 · 实时双图查看器</div>
    <div class="controls">
        <button id="btn-root">📁 选择根目录</button>
        <button id="btn-detect" title="读取 batch_anime2real.py 的输出文件夹并跳转">🔍 自动检测</button>
        <span id="root-path"></span>
        <select id="sel-job"></select>
        <button id="btn-refresh" title="重新扫描任务文件夹">🔄 刷新</button>
        <label class="chk"><input type="checkbox" id="chk-follow" checked> 自动跟随最新</label>
        <button id="btn-pairs">☰ 对比组列表</button>
    </div>
    <div class="status" id="status-bar">正在自动检测 batch_anime2real.py 的输出文件夹…（也可点「📁 选择根目录」手动指定）</div>
</header>

<main>
    <button id="btn-prev" class="nav-btn" title="上一对">◀</button>
    <button id="btn-next" class="nav-btn" title="下一对">▶</button>
    <section class="panel input">
        <div class="panel-title">输入图 (原图)</div>
        <div class="imgwrap">
            <img id="img-input" alt="原图">
            <div id="ph-input" class="placeholder hidden">等待处理…暂无图片</div>
        </div>
        <div class="panel-meta" id="meta-input">—</div>
    </section>
    <section class="panel output">
        <div class="panel-title">输出图 (生成结果)</div>
        <div class="imgwrap">
            <img id="img-output" alt="生成图">
            <div id="ph-output" class="placeholder hidden">等待处理…暂无图片</div>
        </div>
        <div class="panel-meta" id="meta-output">—</div>
    </section>
</main>

<aside id="drawer">
    <div id="drawer-head">
        <b>对比组列表</b>
        <button id="btn-drawer-close">✕ 关闭</button>
    </div>
    <div id="pair-list"></div>
</aside>

<div id="modal" class="hidden">
    <div id="modal-card">
        <div id="modal-head">
            <b>选择任务文件夹</b>
            <button id="btn-modal-close">✕</button>
        </div>
        <div id="modal-path"></div>
        <div id="dir-list"></div>
        <div id="modal-foot">
            <button id="btn-parent">⬆ 上级</button>
            <button id="btn-choose">✓ 选择此文件夹</button>
        </div>
    </div>
</div>

<script>
"use strict";
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

let cfg = { root:"", job:"", follow:true, viewing:null, lastKey:"", manual:false };
let pollTick = 0;

async function getJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
}
function postJSON(url, data) {
    return fetch(url, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(data)
    });
}

function fmtTime(ts) {
    if (!ts) return "—";
    const d = new Date(ts * 1000), now = new Date();
    const p = x => String(x).padStart(2, "0");
    const hm = p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
    return d.toDateString() === now.toDateString() ? hm : p(d.getMonth()+1) + "-" + p(d.getDate()) + " " + hm;
}
function imgURL(job, side, name, mtime) {
    return "/api/image?job=" + encodeURIComponent(job)
         + "&side=" + side
         + "&name=" + encodeURIComponent(name)
         + "&t=" + Math.round(mtime || 0);
}

/* ---------- 双图渲染 ---------- */
function renderPair(pair) {
    cfg.viewing = pair;
    renderSide("input", "control", "原图", pair);
    renderSide("output", "target", "生成图", pair);
}
function renderSide(id, side, label, pair) {
    const img = $("img-" + id), ph = $("ph-" + id);
    if (pair["has_" + side]) {
        img.src = imgURL(cfg.job, side, pair.name, pair[side + "_mtime"]);
        img.classList.remove("hidden");
        ph.classList.add("hidden");
    } else {
        img.classList.add("hidden");
        ph.classList.remove("hidden");
        ph.textContent = "「" + label + "」缺失";
    }
    const t = pair[side + "_mtime"];
    $("meta-" + id).textContent = pair.name + (t ? "  ·  " + fmtTime(t) : "");
}
function renderEmpty(text) {
    cfg.viewing = null;
    for (const id of ["input", "output"]) {
        $("img-" + id).classList.add("hidden");
        $("ph-" + id).classList.remove("hidden");
        $("ph-" + id).textContent = text || "等待处理…暂无图片";
        $("meta-" + id).textContent = "—";
    }
}
function flash() {
    for (const p of document.querySelectorAll(".panel")) {
        p.classList.remove("flash");
        void p.offsetWidth;
        p.classList.add("flash");
    }
}

/* ---------- 状态轮询 ---------- */
function updateStatus(s) {
    let txt;
    if (!s.exists) {
        txt = "任务文件夹不存在或已被删除,请重新选择";
    } else if (!s.latest) {
        txt = "共 0 组对比图 · 等待桌面版处理输出…(处理结果会保存到 control/ 与 target/)";
    } else {
        txt = "共 " + s.count + " 组对比图  ·  最新: " + s.latest.name
            + "  ·  更新于 " + fmtTime(s.latest.max_mtime);
    }
    $("status-bar").textContent = txt + "  ·  扫描: " + fmtTime(Date.now() / 1000);
}

async function poll() {
    pollTick++;
    // 未手动指定目录时,定期跟随桌面版记录的输出文件夹(约每 9 秒检查一次)
    if (!cfg.manual && pollTick % 6 === 1) {
        await autoDetect(true);
    }
    if (cfg.job) {
        try {
            const s = await getJSON("/api/state?root=" + encodeURIComponent(cfg.root)
                                  + "&job=" + encodeURIComponent(cfg.job));
            updateStatus(s);
            if (cfg.follow) {
                const latest = s.latest;
                if (!latest) {
                    renderEmpty();
                    cfg.lastKey = "";
                } else {
                    const key = latest.name + "@" + Math.round(latest.max_mtime);
                    if (key !== cfg.lastKey) {
                        cfg.lastKey = key;
                        renderPair(latest);
                        flash();
                    }
                }
            }
        } catch (e) { /* 服务暂不可用,静默重试 */ }
    }
    setTimeout(poll, 1500);
}

/* ---------- 手动刷新 ---------- */
async function refreshNow() {
    if (!cfg.job) { renderEmpty("请先选择任务文件夹"); updateNavButtons(null, -1); return; }
    try {
        const s = await getJSON("/api/state?root=" + encodeURIComponent(cfg.root)
                              + "&job=" + encodeURIComponent(cfg.job));
        updateStatus(s);
        if (s.latest) {
            cfg.lastKey = s.latest.name + "@" + Math.round(s.latest.max_mtime);
            renderPair(s.latest);
        } else {
            renderEmpty();
        }
    } catch (e) { }
    // 同步导航按钮可用状态(按完整列表计算当前位置)
    try {
        const d = await getJSON("/api/pairs?job=" + encodeURIComponent(cfg.job));
        const pairs = d.pairs || [];
        const cur = cfg.viewing ? cfg.viewing.name : null;
        const idx = cur ? pairs.findIndex(p => p.name === cur) : -1;
        updateNavButtons(pairs, idx);
    } catch (e) { }
}

/* ---------- 自动检测桌面版的输出文件夹 ---------- */
async function autoDetect(quiet) {
    let d;
    try { d = await getJSON("/api/autodetect"); }
    catch (e) { return false; }
    if (!d.ok || !d.root) {
        if (!quiet) alert(d.error || "未检测到输出文件夹");
        return false;
    }
    if (d.root === cfg.root) {
        if (quiet) return true;
        // 目录没变:只是手动触发,刷新一次即可
        await loadJobs(cfg.job);
        return true;
    }
    cfg.root = d.root;
    cfg.manual = false;              // 跟随自动检测,下次启动仍会重新定位
    cfg.lastKey = ""; cfg.viewing = null;
    $("root-path").textContent = d.root;
    await loadJobs(d.job || "");
    return true;
}
$("btn-detect").onclick = () => autoDetect(false);

/* ---------- 根目录 + 任务选择 ---------- */
function joinPath(a, b) {
    if (!a) return b;
    return a.replace(/[\\/]+$/, "") + "\\" + b;
}
function parentPath(p) {
    p = p.replace(/[\\/]+$/, "");
    if (!p) return "";
    if (/^[A-Za-z]:$/.test(p)) return "";      // 磁盘根 → 回到磁盘列表
    const i = Math.max(p.lastIndexOf("\\"), p.lastIndexOf("/"));
    return i < 0 ? "" : p.slice(0, i);
}

let modalPath = "";
async function loadDirs() {
    try {
        const d = await getJSON("/api/dirs?path=" + encodeURIComponent(modalPath));
        if (!d.ok) { $("dir-list").innerHTML = '<div class="dir-empty">' + esc(d.error) + "</div>"; return; }
        modalPath = d.path;
        $("modal-path").textContent = modalPath || "请选择磁盘";
        $("btn-parent").classList.toggle("hidden", !d.parent);
        const list = $("dir-list");
        list.innerHTML = "";
        if (!d.entries.length) {
            list.innerHTML = '<div class="dir-empty">(空文件夹)</div>';
            return;
        }
        for (const e of d.entries) {
            const div = document.createElement("div");
            div.className = "dir-item" + (d.drive ? " drive" : "");
            div.textContent = d.drive ? e : "📁 " + e;
            div.onclick = async () => {
                modalPath = d.drive ? e : joinPath(modalPath, e);
                await loadDirs();
            };
            list.appendChild(div);
        }
    } catch (e) { }
}
function openDirModal() {
    $("modal").classList.remove("hidden");
    modalPath = cfg.root || "";
    loadDirs();
}
$("btn-root").onclick = openDirModal;
$("btn-modal-close").onclick = () => $("modal").classList.add("hidden");
$("btn-parent").onclick = async () => { modalPath = parentPath(modalPath); await loadDirs(); };
$("btn-choose").onclick = () => {
    if (!modalPath) return;
    cfg.root = modalPath;
    cfg.manual = true;               // 手动指定后不再被自动检测覆盖
    $("root-path").textContent = modalPath;
    $("modal").classList.add("hidden");
    loadJobs("");
};

async function loadJobs(prefer) {
    if (!cfg.root) return;
    let d;
    try { d = await getJSON("/api/jobs?root=" + encodeURIComponent(cfg.root)); }
    catch (e) { return; }
    const sel = $("sel-job");
    sel.innerHTML = "";
    const jobs = d.jobs || [];
    if (!jobs.length) {
        const opt = document.createElement("option");
        opt.value = ""; opt.textContent = "（未找到任务文件夹）";
        sel.appendChild(opt);
        cfg.job = "";
        renderEmpty("该目录下没有包含 control/target 的任务文件夹");
        return;
    }
    for (const j of jobs) {
        const opt = document.createElement("option");
        opt.value = j;
        opt.textContent = j === cfg.root ? "（当前目录本身）" : j.split(/[\\/]/).pop();
        opt.title = j;
        sel.appendChild(opt);
    }
    const pick = prefer && jobs.indexOf(prefer) >= 0 ? prefer : jobs[0];
    sel.value = pick;
    onJobChange();
}
function onJobChange() {
    cfg.job = $("sel-job").value || "";
    cfg.lastKey = ""; cfg.viewing = null;
    updateNavButtons(null, -1);
    postJSON("/api/save", { root: cfg.root, job: cfg.job, manual: cfg.manual });
    refreshNow();
}
$("sel-job").onchange = onJobChange;
$("btn-refresh").onclick = () => loadJobs(cfg.job);

/* ---------- 自动跟随开关 ---------- */
$("chk-follow").onchange = () => {
    cfg.follow = $("chk-follow").checked;
    if (cfg.follow) { cfg.lastKey = ""; refreshNow(); }
};

/* ---------- 上一对 / 下一对 导航(按对比组列表顺序) ---------- */
function updateNavButtons(pairs, idx) {
    const has = pairs && pairs.length > 0;
    $("btn-prev").disabled = !has || idx <= 0;
    $("btn-next").disabled = !has || idx >= pairs.length - 1;
}
async function navigate(offset) {
    if (!cfg.job) return;
    let d;
    try { d = await getJSON("/api/pairs?job=" + encodeURIComponent(cfg.job)); }
    catch (e) { return; }
    const pairs = d.pairs || [];
    if (!pairs.length) { updateNavButtons(pairs, -1); return; }
    const cur = cfg.viewing ? cfg.viewing.name : null;
    let idx = cur ? pairs.findIndex(p => p.name === cur) : -1;
    if (idx < 0) idx = 0;                          // 当前不在列表中(如初始状态),从最新一对开始
    idx = Math.max(0, Math.min(pairs.length - 1, idx + offset));
    renderPair(pairs[idx]);
    updateNavButtons(pairs, idx);
    // 手动浏览时自动关闭跟随
    cfg.follow = false;
    $("chk-follow").checked = false;
}
$("btn-prev").onclick = () => navigate(-1);
$("btn-next").onclick = () => navigate(+1);

/* ---------- 对比组列表抽屉 ---------- */
$("btn-pairs").onclick = openDrawer;
$("btn-drawer-close").onclick = () => $("drawer").classList.remove("open");

async function openDrawer() {
    $("drawer").classList.add("open");
    const list = $("pair-list");
    if (!cfg.job) {
        list.innerHTML = '<div class="dir-empty">请先选择任务文件夹</div>';
        return;
    }
    list.innerHTML = '<div class="dir-empty">加载中…</div>';
    let d;
    try { d = await getJSON("/api/pairs?job=" + encodeURIComponent(cfg.job)); }
    catch (e) { list.innerHTML = '<div class="dir-empty">加载失败</div>'; return; }
    const pairs = d.pairs || [];
    list.innerHTML = "";
    if (!pairs.length) {
        list.innerHTML = '<div class="dir-empty">暂无对比图</div>';
        return;
    }
    for (const p of pairs) {
        const item = document.createElement("div");
        item.className = "pair-item";
        const cChip = p.has_control ? '<span class="chip-ok">原✓</span>' : '<span class="chip-miss">原缺</span>';
        const tChip = p.has_target ? '<span class="chip-ok">成✓</span>' : '<span class="chip-miss">成缺</span>';
        item.innerHTML =
            (p.has_control ? '<img loading="lazy" src="' + imgURL(cfg.job, "control", p.name, p.control_mtime) + '">' : '<img style="visibility:hidden">')
          + (p.has_target ? '<img loading="lazy" src="' + imgURL(cfg.job, "target", p.name, p.target_mtime) + '">' : '<img style="visibility:hidden">')
          + '<div class="pair-info"><div class="pair-name" title="' + esc(p.name) + '">' + esc(p.name) + "</div>"
          + '<div class="pair-time">' + fmtTime(p.max_mtime) + "</div>"
          + '<div class="chips">' + cChip + tChip + "</div></div>";
        item.onclick = () => {
            renderPair(p);
            cfg.follow = false;
            $("chk-follow").checked = false;
            $("drawer").classList.remove("open");
        };
        list.appendChild(item);
    }
}

/* ---------- 初始化 ---------- */
(async function init() {
    try {
        const s = await getJSON("/api/settings");
        cfg.manual = !!s.manual;
        if (s.root) {
            cfg.root = s.root;
            $("root-path").textContent = s.root;
            await loadJobs(s.job || "");
        }
    } catch (e) { }
    poll();
})();
</script>
</body>
</html>
"""

# ============================================================
# 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="动漫转写实 网页实时双图查看器")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"监听端口(默认 {DEFAULT_PORT})")
    parser.add_argument("--no-browser", action="store_true", help="启动时不自动打开浏览器")
    args = parser.parse_args()

    ips = get_lan_ips()
    print("=" * 56)
    print("动漫转写实 · 网页实时双图查看器已启动")
    print(f"本机访问:   http://127.0.0.1:{args.port}")
    if ips:
        for ip in ips:
            print(f"局域网访问: http://{ip}:{args.port}")
        print("平板/手机需与电脑连同一 Wi-Fi,在浏览器打开上面地址即可")
    print("(如无法访问,请检查 Windows 防火墙是否放行 Python)")
    print("=" * 56)

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()

    try:
        # threaded=True 允许平板与电脑同时浏览
        app.run(host="0.0.0.0", port=args.port, threaded=True)
    except OSError:
        print(f"端口 {args.port} 被占用,请换一个端口重试: --port 其他端口")
        sys.exit(1)


if __name__ == "__main__":
    main()
