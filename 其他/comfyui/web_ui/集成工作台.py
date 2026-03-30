import streamlit as st
import json
import os
from PIL import Image
import requests
from io import BytesIO
import time
import uuid
import websocket
import traceback
from urllib.parse import urljoin

# ComfyUI 服务器配置
COMFYUI_SERVER = os.getenv("COMFYUI_SERVER", "http://127.0.0.1:8188")
os.environ["PYTHONIOENCODING"] = "utf-8"


class ComfyUIClient:
    """ComfyUI API 客户端封装"""

    def __init__(self, server_address=COMFYUI_SERVER):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())

    def upload_image(self, image_file, subfolder=""):
        """上传图片到 ComfyUI 服务器"""
        try:
            files = {"image": (image_file.name, image_file.getvalue(), image_file.type)}
            response = requests.post(
                urljoin(self.server_address, "/upload/image"),
                files=files,
                timeout=30,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"图片上传失败：{str(e)}")
            raise

    def upload_audio(self, audio_file):
        """上传音频到 ComfyUI 服务器的 input/audio 目录"""
        try:
            files = {
                "file": (audio_file.name, audio_file.getvalue(), audio_file.type),
                "subfolder": ("", "input"),
                "type": ("", "audio")
            }
            response = requests.post(
                urljoin(self.server_address, "/upload/file"),
                files=files,
                timeout=30,
                headers={"Accept": "application/json"}
            )
            
            if not response.ok:
                files = {"image": (audio_file.name, audio_file.getvalue(), audio_file.type)}
                response = requests.post(
                    urljoin(self.server_address, "/upload/image"),
                    files=files,
                    timeout=30,
                    headers={"Accept": "application/json"}
                )
            
            if not response.ok:
                st.error(f"音频上传失败：HTTP {response.status_code}")
                raise Exception(f"音频上传失败")
            
            return {"name": audio_file.name}
        except Exception as e:
            st.error(f"音频上传失败：{str(e)}")
            raise

    def get_image(self, image_filename, subfolder="", folder_type="output"):
        """从 ComfyUI 服务器获取图片/视频"""
        try:
            params = {"filename": image_filename, "subfolder": subfolder, "type": folder_type}
            response = requests.get(
                urljoin(self.server_address, "/view"),
                params=params,
                timeout=60,
                stream=True
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            st.error(f"文件获取失败：{str(e)}")
            raise

    def get_video_from_history(self, prompt_id):
        """从 ComfyUI 历史中获取视频信息"""
        try:
            history = self.get_history(prompt_id)
            if prompt_id not in history:
                return None, None
            
            outputs = history[prompt_id].get("outputs", {})
            for node_id, node_data in outputs.items():
                for key in ["videos", "gifs"]:
                    if key in node_data and len(node_data[key]) > 0:
                        video_info = node_data[key][0]
                        return video_info["filename"], video_info.get("subfolder", "")
            return None, None
        except Exception as e:
            st.error(f"解析视频信息失败：{str(e)}")
            return None, None

    def queue_prompt(self, workflow):
        """提交工作流到 ComfyUI 队列"""
        try:
            payload = {"prompt": workflow, "client_id": self.client_id}
            response = requests.post(
                urljoin(self.server_address, "/prompt"),
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("prompt_id", str(uuid.uuid4())), self.client_id
        except Exception as e:
            st.error(f"提交工作流失败：{str(e)}")
            raise

    def get_history(self, prompt_id):
        """获取执行历史"""
        try:
            response = requests.get(
                urljoin(self.server_address, f"/history/{prompt_id}"),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"获取执行历史失败：{str(e)}")
            raise

    def wait_for_completion(self, prompt_id, timeout=120):
        """等待任务完成"""
        start_time = time.time()
        ws_url = self.server_address.replace("http://", "ws://").replace("https://", "wss://")

        max_retry = 3
        retry_count = 0

        while retry_count < max_retry:
            try:
                ws = websocket.WebSocket()
                ws.connect(f"{ws_url}/ws?clientId={self.client_id}", timeout=10)
                break
            except Exception as e:
                retry_count += 1
                st.warning(f"WebSocket 连接失败，重试 {retry_count}/{max_retry}：{str(e)}")
                time.sleep(2)
                if retry_count >= max_retry:
                    raise ConnectionError(f"WebSocket 连接失败：{str(e)}")

        try:
            while True:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"任务执行超时（{timeout}秒）")

                ws.settimeout(5)
                try:
                    message = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception as e:
                    if "timed out" in str(e).lower():
                        continue
                    raise

                if not message:
                    continue
                    
                if isinstance(message, str):
                    try:
                        msg = json.loads(message)
                        if msg.get("type") == "executing":
                            data = msg.get("data", {})
                            if data.get("node") is None and data.get("prompt_id") == prompt_id:
                                break
                        elif msg.get("type") == "status":
                            status = msg.get("data", {}).get("status", {})
                            if status.get("errors"):
                                errors = status["errors"]
                                raise RuntimeError(f"ComfyUI 执行错误：{json.dumps(errors, ensure_ascii=False)}")
                    except json.JSONDecodeError:
                        continue
        finally:
            ws.close()

        return self.get_history(prompt_id)


def check_comfyui_connection(server_address):
    """测试 ComfyUI 连接"""
    try:
        response = requests.get(urljoin(server_address, "/system_stats"), timeout=5)
        return response.status_code == 200
    except Exception:
        return False


# 页面配置
st.set_page_config(
    page_title="AI 视觉处理集成工作台",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .stButton>button {
        width: 100%;
        background-color: #1E88E5;
        color: white;
        font-weight: bold;
        padding: 12px;
        border-radius: 8px;
        border: none;
        font-size: 1rem;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    .tool-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        color: white;
    }
    .tool-card h3 {
        margin-top: 0;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 标题区域
st.markdown('<div class="main-header">🚀 AI 视觉处理集成工作台</div>', unsafe_allow_html=True)
#st.markdown('<div class="sub-header">综合 ComfyUI 工作流的图像视频生成工具集</div>', unsafe_allow_html=True)

# 侧边栏导航
with st.sidebar:
    st.header("📑 工具导航")
    
    tool = st.radio(
        "选择工具",
        [
            "🎬 Wan2.2 首尾帧视频生成器",
            "🎨 Qwen-Image 多模式编辑器",
            "🖼️ Qwen-Image 图像生成器",
            "👤 数字人视频拼接"
        ],
        index=0,
        help="选择要使用的 AI 工具"
    )
    
    st.markdown("---")
    
    # ComfyUI 连接状态
    st.subheader("🔌 ComfyUI 服务状态")
    if check_comfyui_connection(COMFYUI_SERVER):
        st.success("✅ 已连接")
    else:
        st.error(f"❌ 无法连接到 {COMFYUI_SERVER}")
        st.warning("请先启动 ComfyUI 服务器")

# 根据选择显示对应工具
if tool == "🎬 Wan2.2 首尾帧视频生成器":
    # Wan2.2 视频生成器子页面
    st.markdown('<div class="tool-card">', unsafe_allow_html=True)
    st.header("🎬 Wan2.2 首尾帧视频生成器")
    st.markdown('基于 ComfyUI 工作流的交互式视频生成工具，支持首尾帧控制')
    st.markdown('</div>')
    
    # 侧边栏 - 高级设置
    with st.sidebar:
        st.header("⚙️ 采样设置")
        
        total_steps = st.number_input("总步数", min_value=1, max_value=100, value=6)
        high_noise_steps = st.number_input("高噪阶段步数", min_value=1, max_value=total_steps, value=3)
        
        frame_rate = st.number_input("帧率 (fps)", min_value=1, max_value=60, value=16)
        bitrate = st.number_input("比特率 (Mbps)", min_value=1, max_value=50, value=10)
        video_length = st.number_input("视频长度 (帧数)", min_value=1, max_value=240, value=81)
        
        seed = st.number_input("随机种子", min_value=0, max_value=(1 << 53) - 1, value=807591005692968)
        
        filename_prefix = st.text_input("文件名前缀", value="wan22_i2v")
    
    # 图像输入区域
    col1, col2 = st.columns(2)
    with col1:
        start_image = st.file_uploader("上传首帧图像", type=["png", "jpg", "jpeg"], key="start_img")
        if start_image:
            st.image(start_image, caption="首帧图像", use_container_width=True)
    
    with col2:
        end_image = st.file_uploader("上传尾帧图像", type=["png", "jpg", "jpeg"], key="end_img")
        if end_image:
            st.image(end_image, caption="尾帧图像", use_container_width=True)
    
    # 提示词区域
    positive_prompt = st.text_area(
        "正向提示词",
        value="镜头中景全身侧坐开始，镜头拉远，旋转运镜，双腿屈膝交叠，双手叉腰，切镜中景正面全身正面坐姿，镜头拉近，双腿屈膝，双手抬起摸发饰发饰，切镜近景全身侧身跪姿，旋转运镜，单膝跪地",
        height=100,
        help="描述期望的视频内容和运镜方式"
    )
    
    negative_prompt = st.text_area(
        "负向提示词",
        value="色彩艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG 压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，畸形的肢体，杂乱的背景",
        height=80,
        help="描述需要避免的内容"
    )
    
    # 生成按钮
    if st.button("🚀 生成视频", type="primary"):
        if not positive_prompt.strip():
            st.error("❌ 请输入正向提示词！")
        elif check_comfyui_connection(COMFYUI_SERVER):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                client = ComfyUIClient()
                progress_bar.progress(10)
                
                # 上传图像
                start_filename = None
                end_filename = None
                
                if start_image:
                    result = client.upload_image(start_image)
                    start_filename = result["name"]
                
                if end_image:
                    result = client.upload_image(end_image)
                    end_filename = result["name"]
                
                progress_bar.progress(30)
                status_text.markdown('⚙️ 正在加载工作流...')
                
                # 加载工作流 JSON
                workflow_path = r"其他/comfyui/工作流/wan2.2i2v_首尾帧.json"
                if not os.path.exists(workflow_path):
                    st.error(f"未找到工作流文件：{workflow_path}")
                    st.stop()
                
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                
                # 配置参数
                workflow["6"]["inputs"]["text"] = positive_prompt.strip() if "6" in workflow else ""
                if "7" in workflow:
                    workflow["7"]["inputs"]["text"] = negative_prompt.strip()


                progress_bar.progress(50)
                
                # 提交任务
                prompt_id, _ = client.queue_prompt(workflow)
                st.success(f"✅ 任务已提交，Prompt ID: {prompt_id}")
                progress_bar.progress(60)
                
                status_text.markdown('⏳ 正在生成视频...')
                history = client.wait_for_completion(prompt_id, timeout=600)
                progress_bar.progress(80)
                
                # 获取结果
                video_filename, _ = client.get_video_from_history(prompt_id)
                
                if video_filename:
                    video_data = client.get_image(video_filename)
                    progress_bar.progress(100)
                    status_text.markdown('✅ 视频生成完成！')
                    
                    st.video(video_data)
                    st.download_button("📥 下载视频", video_data, f"{filename_prefix}_{prompt_id}.mp4", "video/mp4")
                else:
                    st.warning("⚠️ 未找到生成的视频文件")
            
            except Exception as e:
                st.error(f"❌ 生成失败：{str(e)}")
                with st.expander("详细错误信息"):
                    st.code(traceback.format_exc())

elif tool == "🎨 Qwen-Image 多模式编辑器":
    # Qwen 图像编辑器子页面
    st.markdown('<div class="tool-card">', unsafe_allow_html=True)
    st.header("🎨 Qwen-Image 多模式图像编辑器")
    st.markdown('支持单图、双图、三图的智能编辑功能')
    st.markdown('</div>')
    
    # 侧边栏设置
    with st.sidebar:
        seed = st.number_input("随机种子", min_value=0, max_value=2**53-1, value=int(time.time()) % (2**53))
        
        col1, col2 = st.columns(2)
        with col1:
            width = st.number_input("宽度", min_value=256, max_value=2048, value=1056)
        with col2:
            height = st.number_input("高度", min_value=256, max_value=2048, value=1584)
        
        filename_prefix = st.text_input("文件名前缀", value="QwenEdit")
    
    # 模式选择
    mode = st.radio("🎯 编辑模式", ["单图编辑", "双图编辑", "三图编辑"], index=0)
    
    # 图片上传
    uploaded_images = []
    
    if mode == "单图编辑":
        img = st.file_uploader("上传图片", type=["png", "jpg", "jpeg"], key="qwen_single")
        if img:
            uploaded_images.append(img)
            st.image(img, use_container_width=True)
    
    elif mode == "双图编辑":
        c1, c2 = st.columns(2)
        with c1:
            img1 = st.file_uploader("图片 1（原图）", type=["png", "jpg", "jpeg"], key="qwen_double_1")
            if img1:
                uploaded_images.append(img1)
                st.image(img1, use_container_width=True)
        with c2:
            img2 = st.file_uploader("图片 2（参考图）", type=["png", "jpg", "jpeg"], key="qwen_double_2")
            if img2:
                uploaded_images.append(img2)
                st.image(img2, use_container_width=True)
    
    elif mode == "三图编辑":
        cols = st.columns(3)
        for i in range(3):
            img = st.file_uploader(f"图片 {i+1}", type=["png", "jpg", "jpeg"], key=f"qwen_triple_{i}")
            if img:
                uploaded_images.append(img)
    
    # 提示词输入
    prompt = st.text_area("编辑指令", value="让图 1 的人物穿上图 2 的衣服", height=80)
    
    # 生成按钮
    if st.button("🚀 开始编辑", type="primary"):
        if not prompt.strip():
            st.error("❌ 请输入编辑指令！")
        elif check_comfyui_connection(COMFYUI_SERVER):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                client = ComfyUIClient()
                
                # 加载工作流
                workflow_paths = {
                    "单图编辑": r"其他/comfyui/工作流/单图编辑.json",
                    "双图编辑": r"其他/comfyui/工作流/双图编辑.json",
                    "三图编辑": r"其他/comfyui/工作流/三图编辑.json"
                }
                
                workflow_path = workflow_paths.get(mode)
                if not os.path.exists(workflow_path):
                    st.error(f"未找到工作流文件：{workflow_path}")
                    st.stop()
                
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                
                progress_bar.progress(30)
                
                # 上传图片
                uploaded_filenames = []
                for img in uploaded_images:
                    result = client.upload_image(img)
                    uploaded_filenames.append(result["name"])
                
                progress_bar.progress(50)
                
                # 配置工作流
                if "4" in workflow and "seed" in workflow["4"].get("inputs", {}):
                    workflow["4"]["inputs"]["seed"] = int(seed)
                if "8" in workflow:
                    workflow["8"]["inputs"]["prompt"] = prompt.strip()
                
                progress_bar.progress(60)
                
                # 提交任务
                prompt_id, _ = client.queue_prompt(workflow)
                st.success(f"✅ 任务已提交，Prompt ID: {prompt_id}")
                progress_bar.progress(70)
                
                status_text.markdown('⏳ 正在生成图像...')
                history = client.wait_for_completion(prompt_id, timeout=180)
                progress_bar.progress(90)
                
                # 获取结果
                if prompt_id in history:
                    output = history[prompt_id].get("outputs", {})
                    
                    for node_id, node_data in output.items():
                        if "images" in node_data:
                            img_info = node_data["images"][0]
                            response = requests.get(
                                f"{COMFYUI_SERVER}/view?filename={img_info['filename']}&subfolder={img_info.get('subfolder', '')}&type=output",
                                stream=True
                            )
                            
                            img = Image.open(BytesIO(response.content))
                            st.image(img, use_container_width=True)
                            st.download_button("📥 下载图像", response.content, f"{filename_prefix}_{prompt_id}.png", "image/png")
                            break
            
            except Exception as e:
                st.error(f"❌ 编辑失败：{str(e)}")

elif tool == "🖼️ Qwen-Image 图像生成器":
    # Qwen 图像生成器子页面
    st.markdown('<div class="tool-card">', unsafe_allow_html=True)
    st.header("🖼️ Qwen-Image 图像生成器")
    st.markdown('基于 Lightning 4 步快速生成的 AI 图像创作工具')
    st.markdown('</div>')
    
    # 侧边栏设置
    with st.sidebar:
        seed = st.number_input("随机种子", min_value=0, max_value=2**53-1, value=int(time.time()) % (2**53))
        steps = st.slider("生成步数", min_value=1, max_value=10, value=4)
        cfg = st.number_input("CFG 值", min_value=0.0, max_value=20.0, value=1.0, step=0.5)
        
        col1, col2 = st.columns(2)
        with col1:
            width = st.number_input("宽度", min_value=256, max_value=2048, value=1056)
        with col2:
            height = st.number_input("高度", min_value=256, max_value=2048, value=1584)
        
        filename_prefix = st.text_input("文件名前缀", value="QwenImage")
    
    # 提示词输入区域
    positive_prompt = st.text_area(
        "正向提示词",
        value="卡通 3D 风格海报，欢乐明亮。背景是春日蓝天白云下的户外踏青场景：绿色草地上点缀着五彩鲜花和飞舞的蝴蝶，远处有风筝在天空飘扬，草地上摆放着野餐毯和彩色遮阳伞。前景是一位卡通小朋友手持风筝线，画面 Q 萌治愈。",
        height=150,
        help="详细描述要生成的图像内容"
    )
    
    negative_prompt = st.text_area(
        "负向提示词",
        value="低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，过度光滑，文字模糊，扭曲",
        height=80,
        help="描述需要避免的内容"
    )
    
    # 生成按钮
    if st.button("🚀 开始生成", type="primary"):
        if not positive_prompt.strip():
            st.error("❌ 请输入正向提示词！")
        elif check_comfyui_connection(COMFYUI_SERVER):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                client = ComfyUIClient()
                
                # 加载工作流
                workflow_path = r"其他/comfyui/工作流/Qwen-Image-2512-4 步.json"
                if not os.path.exists(workflow_path):
                    st.error(f"未找到工作流文件：{workflow_path}")
                    st.stop()
                
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                
                # 配置参数
                if "3" in workflow:
                    workflow["3"]["inputs"]["seed"] = int(seed)
                    workflow["3"]["inputs"]["steps"] = steps
                    workflow["3"]["inputs"]["cfg"] = cfg
                if "58" in workflow:
                    workflow["58"]["inputs"]["width"] = width
                    workflow["58"]["inputs"]["height"] = height
                if "60" in workflow:
                    workflow["60"]["inputs"]["filename_prefix"] = filename_prefix
                
                for node_id in ["6"]:
                    if node_id in workflow:
                        workflow[node_id]["inputs"]["text"] = positive_prompt.strip()
                
                for node_id in ["7"]:
                    if node_id in workflow:
                        workflow[node_id]["inputs"]["text"] = negative_prompt.strip()
                
                progress_bar.progress(50)
                
                # 提交任务
                prompt_id, _ = client.queue_prompt(workflow)
                st.success(f"✅ 任务已提交，Prompt ID: {prompt_id}")
                progress_bar.progress(60)
                
                status_text.markdown('⏳ 正在生成图像...')
                history = client.wait_for_completion(prompt_id, timeout=120)
                progress_bar.progress(80)
                
                # 获取结果
                if prompt_id in history:
                    output = history[prompt_id].get("outputs", {})
                    
                    for node_id, node_data in output.items():
                        if "images" in node_data:
                            img_info = node_data["images"][0]
                            response = requests.get(
                                f"{COMFYUI_SERVER}/view?filename={img_info['filename']}&subfolder={img_info.get('subfolder', '')}&type=output",
                                stream=True
                            )
                            
                            img = Image.open(BytesIO(response.content))
                            st.image(img, use_container_width=True)
                            st.download_button("📥 下载图像", response.content, f"{filename_prefix}_{prompt_id}.png", "image/png")
                            break
            
            except Exception as e:
                st.error(f"❌ 生成失败：{str(e)}")

elif tool == "👤 数字人视频拼接":
    # 数字人视频拼接子页面
    st.markdown('<div class="tool-card">', unsafe_allow_html=True)
    st.header("👤 数字人视频拼接生成器")
    st.markdown('基于音频驱动的数字人视频生成工具')
    st.markdown('</div>')
    
    # 侧边栏设置
    with st.sidebar:
        total_steps = st.number_input("总步数", min_value=1, max_value=100, value=4)
        frame_rate = st.number_input("帧率 (fps)", min_value=1, max_value=60, value=25)
        video_length = st.number_input("视频长度 (帧数)", min_value=1, max_value=240, value=109)
        filename_prefix = st.text_input("文件名前缀", value="INF")
    
    # 主界面布局
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_image = st.file_uploader("初始图像", type=["png", "jpg", "jpeg"], key="avatar_img")
        if uploaded_image:
            st.image(uploaded_image, caption="数字人初始图像", use_container_width=True)
        
        uploaded_audio = st.file_uploader("音频文件", type=["mp3", "wav", "m4a", "ogg"], key="avatar_audio")
        if uploaded_audio:
            st.audio(uploaded_audio)
    
    with col2:
        action_prompt = st.text_area(
            "每行一个动作描述",
            value="女人在讲话，讲解动作，做手势\n女人微笑，点头示意\n女人挥手告别",
            height=150,
            help="数字人的动作描述，每行一个"
        )
        
        negative_prompt = st.text_area(
            "负向提示词",
            value="色调艳丽，过曝，静态，细节模糊不清，字幕，畸形，毁容的，杂乱的背景，三条腿",
            height=80,
            help="描述需要避免的内容"
        )
    
    # 生成按钮
    if st.button("🚀 生成数字人视频", type="primary"):
        if uploaded_image is None:
            st.error("❌ 请上传初始图像！")
        elif uploaded_audio is None:
            st.error("❌ 请上传音频文件！")
        elif check_comfyui_connection(COMFYUI_SERVER):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                client = ComfyUIClient()
                
                # 上传图片
                image_result = client.upload_image(uploaded_image)
                image_filename = image_result["name"]
                
                audio_result = client.upload_audio(uploaded_audio)
                audio_filename = audio_result["name"]
                
                progress_bar.progress(30)
                
                # 加载工作流
                workflow_path = r"其他/comfyui/工作流/数字人视频批量拼接.json"
                if not os.path.exists(workflow_path):
                    st.error(f"未找到工作流文件：{workflow_path}")
                    st.stop()
                
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                
                # 配置参数
                if "112" in workflow:
                    workflow["112"]["inputs"]["image"] = image_filename
                if "119" in workflow:
                    workflow["119"]["inputs"]["audio"] = audio_filename
                if "127" in workflow:
                    workflow["127"]["inputs"]["text"] = action_prompt.strip()
                
                progress_bar.progress(50)
                
                # 提交任务
                prompt_id, _ = client.queue_prompt(workflow)
                st.success(f"✅ 任务已提交，Prompt ID: {prompt_id}")
                progress_bar.progress(60)
                
                status_text.markdown('⏳ 正在生成视频...')
                history = client.wait_for_completion(prompt_id, timeout=600)
                progress_bar.progress(80)
                
                # 获取结果
                video_filename, _ = client.get_video_from_history(prompt_id)
                
                if video_filename:
                    video_data = client.get_image(video_filename)
                    progress_bar.progress(100)
                    
                    st.video(video_data)
                    st.download_button("📥 下载视频", video_data, f"{filename_prefix}_{prompt_id}.mp4", "video/mp4")
                else:
                    st.warning("⚠️ 未找到生成的视频文件")
            
            except Exception as e:
                st.error(f"❌ 生成失败：{str(e)}")

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>💡 提示：确保 ComfyUI 服务正在运行，并且已安装所有必要的自定义节点</p>
    <p>🔧 基于 ComfyUI API 的 AI 视觉处理工具集</p>
</div>
""", unsafe_allow_html=True)
