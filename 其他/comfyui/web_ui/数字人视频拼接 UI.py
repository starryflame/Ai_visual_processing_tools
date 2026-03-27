import streamlit as st
import json
import os
from PIL import Image
import requests
from io import BytesIO
import base64
import time
import uuid
import websocket
from urllib.parse import urljoin
import traceback

# ComfyUI 服务器配置
COMFYUI_SERVER = os.getenv("COMFYUI_SERVER", "http://127.0.0.1:8188")

# 确保中文路径和字符编码正常
os.environ["PYTHONIOENCODING"] = "utf-8"

class ComfyUIClient:
    """ComfyUI API 客户端封装"""
    def __init__(self, server_address=COMFYUI_SERVER):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
    
    def upload_image(self, image_file):
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
        """上传音频到 ComfyUI 服务器"""
        try:
            files = {"audio": (audio_file.name, audio_file.getvalue(), audio_file.type)}
            response = requests.post(
                urljoin(self.server_address, "/upload/audio"),
                files=files,
                timeout=30,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"音频上传失败：{str(e)}")
            raise

    def get_image(self, image_filename, subfolder="", folder_type="output"):
        """从 ComfyUI 服务器获取图片/视频"""
        try:
            params = {
                "filename": image_filename,
                "subfolder": subfolder,
                "type": folder_type
            }
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
            
            prompt_history = history[prompt_id]
            outputs = prompt_history.get("outputs", {})
            
            # 遍历所有节点查找视频输出
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
            payload = {
                "prompt": workflow,
                "client_id": self.client_id,
            }
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

    def wait_for_completion(self, prompt_id, timeout=600):
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

# 页面配置
st.set_page_config(
    page_title="数字人视频拼接",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stTextArea label, .stTextInput label, .stNumberInput label {
        font-weight: bold;
        color: #333;
    }
    .upload-section {
        background-color: #f5f5f5;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .prompt-section {
        background-color: #e3f2fd;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .result-section {
        background-color: #f1f8e9;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
        max-width: 1200px;
        margin-left: auto;
        margin-right: auto;
        border: 1px solid #c5e1a5;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .result-section video {
        max-width: 100% !important;
        max-height: 75vh !important;
        width: auto !important;
        height: auto !important;
        object-fit: contain !important;
        display: block !important;
        margin: 0 auto !important;
        border-radius: 8px !important;
        border: 1px solid #ddd !important;
    }
    .stButton>button {
        width: 100%;
        background-color: #1E88E5;
        color: white;
        font-weight: bold;
        padding: 15px;
        border-radius: 8px;
        border: none;
        font-size: 1.1rem;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    video {
        max-height: 80vh !important;
        width: auto !important;
        height: auto !important;
        object-fit: contain !important;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<div class="main-header">🎬 数字人视频拼接生成器</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">基于 ComfyUI WanInfiniteTalkToVideo 工作流</div>', unsafe_allow_html=True)

# 侧边栏 - 高级设置
with st.sidebar:
    st.header("⚙️ 高级设置")
    
    # 采样参数
    st.subheader("采样设置")
    total_steps = st.number_input("总步数", min_value=1, max_value=100, value=4, help="KSampler 的总步数")
    
    # 模型配置
    st.subheader("模型配置")
    model_name = st.text_input(
        "主模型名称", 
        value="wan2.1_i2v_480p_scaled_fp8_e4m3_lightx2v_4step_comfyui.safetensors",
        help="Wan 视频生成模型"
    )
    clip_name = st.text_input(
        "CLIP 模型名称", 
        value="umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    )
    vae_name = st.text_input("VAE 模型名称", value="Wan2_1_VAE_bf16.safetensors")
    patch_name = st.text_input(
        "谈话补丁名称", 
        value="Wan2_1-InfiniTetalk-Single_fp16.safetensors"
    )
    audio_encoder = st.text_input(
        "音频编码器名称", 
        value="wav2vec2-chinese-base_fp16.safetensors"
    )
    clip_vision = st.text_input("CLIP Vision 模型", value="clip_vision_h.safetensors")
    
    # 视频输出设置
    st.subheader("视频输出")
    frame_rate = st.number_input("帧率 (fps)", min_value=1, max_value=60, value=25)
    video_length = st.number_input("视频长度 (帧数)", min_value=1, max_value=240, value=109)
    image_width = st.number_input("图像宽度 (px)", min_value=256, max_value=1920, value=1024)
    filename_prefix = st.text_input("文件名前缀", value="INF")
    
    # ComfyUI 连接测试
    st.subheader("🔌 连接测试")
    if st.button("测试 ComfyUI 连接"):
        try:
            response = requests.get(urljoin(COMFYUI_SERVER, "/system_stats"), timeout=5)
            if response.status_code == 200:
                st.success("✅ ComfyUI 连接成功！")
            else:
                st.error(f"❌ 连接失败：状态码 {response.status_code}")
        except Exception as e:
            st.error(f"❌ 连接失败：{str(e)}")

# 主界面布局
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    
    # 图像上传
    st.header("🖼️ 初始图像")
    uploaded_image = st.file_uploader(
        "上传图片",
        type=["png", "jpg", "jpeg"],
        key="uploaded_image",
        help="数字人的初始图像（首帧）"
    )
    
    if uploaded_image:
        st.image(uploaded_image, caption="上传的初始图像", use_container_width=True)
    
    # 音频上传
    st.header("🎵 音频文件")
    uploaded_audio = st.file_uploader(
        "上传音频",
        type=["mp3", "wav", "m4a"],
        key="uploaded_audio",
        help="驱动数字人说话的音频文件"
    )
    
    if uploaded_audio:
        st.audio(uploaded_audio, format='audio/mp3')
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="prompt-section">', unsafe_allow_html=True)
    
    # 动作提示词输入
    st.header("📝 动作提示词")
    action_prompt = st.text_area(
        "每行一个动作描述",
        value="女人在讲话，讲解动作，坐手势\n女人在讲话，讲解动作，坐手势",
        height=200,
        help="输入数字人的动作描述，每行一个。程序会自动循环使用这些提示词生成视频。\n\n示例：\n女人在讲话，讲解动作，坐手势\n女人微笑，点头示意\n女人挥手告别"
    )
    
    # 负向提示词
    negative_prompt = st.text_area(
        "负向提示词",
        value="色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG 压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走",
        height=100,
        help="描述需要避免的内容和质量问题"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)

# 生成按钮
st.markdown("---")
generate_btn = st.button("🚀 生成数字人视频", type="primary")

if generate_btn:
    # 验证输入
    if uploaded_image is None:
        st.error("❌ 请上传初始图像！")
        st.stop()
    
    if uploaded_audio is None:
        st.error("❌ 请上传音频文件！")
        st.stop()
    
    if not action_prompt.strip():
        st.error("❌ 请输入动作提示词！")
        st.stop()
    
    # 显示进度
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">📋 准备生成视频...</div>', unsafe_allow_html=True)
    
    try:
        # 初始化客户端
        client = ComfyUIClient()
        
        progress_bar.progress(10)
        
        # 上传图像和音频
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">📤 正在上传文件...</div>', unsafe_allow_html=True)
        
        image_result = client.upload_image(uploaded_image)
        image_filename = image_result["name"]
        st.info(f"图像上传成功：{image_filename}")
        
        audio_result = client.upload_audio(uploaded_audio)
        audio_filename = audio_result["name"]
        st.info(f"音频上传成功：{audio_filename}")
        
        progress_bar.progress(30)
        
        # 加载工作流 JSON
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">⚙️ 正在加载工作流配置...</div>', unsafe_allow_html=True)
        
        workflow_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "工作流",
            "数字人视频批量拼接.json"
        )
        # 兼容不同运行路径
        if not os.path.exists(workflow_path):
            workflow_path = r"其他/comfyui/工作流/数字人视频批量拼接.json"
        
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"未找到工作流 JSON 文件：{workflow_path}")

        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        progress_bar.progress(40)
        
        # 配置工作流参数
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">🔧 正在配置工作流...</div>', unsafe_allow_html=True)
        
        # 节点 112 - LoadImage (初始图像)
        workflow["112"]["inputs"]["image"] = image_filename
        
        # 节点 119 - LoadAudio (音频文件)
        workflow["119"]["inputs"]["audio"] = audio_filename
        
        # 节点 127 - TextInput_ (动作提示词，每行一个)
        action_lines = [line.strip() for line in action_prompt.strip().split('\n') if line.strip()]
        prompt_text = '\n'.join(action_lines * ((len(action_lines) + 9) // len(action_lines)))  # 循环直到至少 10 行
        workflow["127"]["inputs"]["text"] = prompt_text
        
        # 节点 1/24 - CLIPTextEncode (负向提示词)
        for node_id in ["1", "24"]:
            workflow[node_id]["inputs"]["text"] = negative_prompt
        
        # 节点 98 - ImageScaleByAspectRatio V2 (图像尺寸)
        workflow["98"]["inputs"]["scale_to_length"] = [int(image_width)]
        
        # 节点 99 - easy int (宽度值)
        workflow["99"]["inputs"]["value"] = int(image_width)
        
        # 节点 101 - easy int (视频长度)
        workflow["101"]["inputs"]["value"] = int(video_length)
        
        # 节点 102 - PrimitiveFloat (帧率)
        workflow["102"]["inputs"]["value"] = float(frame_rate)
        
        # 节点 103 - easy int (采样步数)
        workflow["103"]["inputs"]["value"] = int(total_steps)
        
        # 节点 85/110 - WanInfiniteTalkToVideo (模型配置)
        workflow["85"]["inputs"]["model_name"] = model_name
        workflow["85"]["inputs"]["length"] = video_length
        
        # 模型加载器配置
        workflow["113"]["inputs"]["model_name"] = model_name
        workflow["114"]["inputs"]["clip_name"] = clip_name
        workflow["115"]["inputs"]["vae_name"] = vae_name
        workflow["116"]["inputs"]["name"] = patch_name
        workflow["117"]["inputs"]["audio_encoder_name"] = audio_encoder
        workflow["118"]["inputs"]["clip_name"] = clip_vision
        
        # VHS_VideoCombine 节点 (视频输出)
        workflow["143"]["inputs"]["frame_rate"] = float(frame_rate)
        workflow["143"]["inputs"]["filename_prefix"] = filename_prefix
        
        progress_bar.progress(50)
        
        # 提交工作流
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">🚀 正在提交任务到 ComfyUI...</div>', unsafe_allow_html=True)
        
        prompt_id, client_id = client.queue_prompt(workflow)
        st.success(f"任务提交成功，Prompt ID: {prompt_id}")
        
        progress_bar.progress(60)
        
        # 等待执行完成
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">⏳ 正在生成视频（可能需要几分钟）...</div>', unsafe_allow_html=True)
        
        history = client.wait_for_completion(prompt_id, timeout=600)
        progress_bar.progress(80)
        
        # 获取生成的视频
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">📥 正在获取生成的视频...</div>', unsafe_allow_html=True)
        
        video_filename, video_subfolder = client.get_video_from_history(prompt_id)
        
        if video_filename:
            video_data = client.get_image(video_filename, subfolder=video_subfolder, folder_type="output")
            
            progress_bar.progress(100)
            status_text.markdown('<div class="status-box" style="background-color: #c8e6c9;">✅ 视频生成完成！</div>', unsafe_allow_html=True)
            
            # 显示结果
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.header("🎉 生成结果")
            
            download_filename = f"{filename_prefix}_{prompt_id}.mp4"
            
            col_result1, col_result2 = st.columns(2)
            
            with col_result1:
                # 显示视频
                st.subheader("生成的视频")
                st.video(video_data)
                
                # 下载按钮
                st.download_button(
                    label="📥 下载视频",
                    data=video_data,
                    file_name=download_filename,
                    mime="video/mp4"
                )
            
            with col_result2:
                # 显示输入信息
                st.subheader("输入信息")
                st.markdown(f"**初始图像**: {image_filename}")
                st.markdown(f"**音频文件**: {audio_filename}")
                st.markdown(f"**动作提示词行数**: {len(action_lines)}")
                st.markdown(f"**视频长度**: {video_length} 帧")
                st.markdown(f"**帧率**: {frame_rate} fps")
                
                with st.expander("📋 查看完整工作流配置"):
                    st.json(workflow)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ 未找到生成的视频文件，请检查 ComfyUI 日志")
            with st.expander("📋 查看执行历史"):
                st.json(history)
    
    except Exception as e:
        st.error(f"❌ 生成失败：{str(e)}")
        progress_bar.progress(0)
        status_text.markdown('<div class="status-box" style="background-color: #ffcdd2;">❌ 生成失败！</div>', unsafe_allow_html=True)
        with st.expander("🔍 详细错误信息"):
            st.code(traceback.format_exc(), language="python")

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>💡 提示：确保 ComfyUI 服务正在运行，并且已安装所有必要的自定义节点</p>
    <p>🔧 技术支持：基于 WanInfiniteTalkToVideo 的数字人视频生成工作流</p>
</div>
""", unsafe_allow_html=True)
