import streamlit as st
import json
import os
from PIL import Image
import requests
from io import BytesIO
import base64
import time
import uuid
import websocket  # 需要安装：pip install websocket-client
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
            
            # 查找视频输出节点 (100)
            if "100" in outputs:
                output_data = outputs["100"]
                for key in ["videos", "gifs", "images"]:
                    if key in output_data and len(output_data[key]) > 0:
                        video_info = output_data[key][0]
                        return video_info["filename"], video_info.get("subfolder", "")
            
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
                # 连接时设置超时
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
                
                # 设置接收超时为 5 秒，避免阻塞
                ws.settimeout(5)
                try:
                    # 移除 recv 中的 timeout 参数，依赖 settimeout
                    message = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception as e:
                    # 处理其他可能的接收异常
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
    page_title="Wan2.2 首尾帧视频生成",
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
    /* 👇 这是修复后的视频样式，强制限制高度 */
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
            /* 全局暴力限制所有视频 */
    video {
        max-height: 80vh !important;
        width: auto !important;
        height: auto !important;
        object-fit: contain !important;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<div class="main-header">🎬 Wan2.2 首尾帧视频生成器</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">基于 ComfyUI 工作流的交互式视频生成工具</div>', unsafe_allow_html=True)

# 侧边栏 - 高级设置
with st.sidebar:
    st.header("⚙️ 高级设置")
    
    # 采样参数
    st.subheader("采样设置")
    total_steps = st.number_input("总步数", min_value=1, max_value=100, value=6, help="KSampler 的总步数")
    high_noise_steps = st.number_input("高噪阶段步数", min_value=1, max_value=total_steps, value=3, help="第一阶段的步数")
    
    # 模型设置
    st.subheader("模型配置")
    unet_high = st.text_input("高噪 UNet 模型", value="wan2.2\\Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors")
    unet_low = st.text_input("低噪 UNet 模型", value="wan2.2\\Wan2_2-I2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors")
    clip_model = st.text_input("CLIP 模型", value="umt5_xxl_fp8_e4m3fn_scaled.safetensors")
    vae_model = st.text_input("VAE 模型", value="wan\\Wan2_1_VAE_bf16.safetensors")
    
    # LoRA 设置
    st.subheader("LoRA 配置")
    lora_high_noise = st.text_input("高噪 LoRA", value="wan\\i2v\\wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors")
    lora_low_noise = st.text_input("低噪 LoRA", value="wan\\i2v\\wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors")
    custom_lora = st.text_input("自定义运镜 LoRA", value="自创\\wan2.2\\高噪\\i2v\\运镜3-22.safetensors")
    
    # 视频输出设置
    st.subheader("视频输出")
    frame_rate = st.number_input("帧率", min_value=1, max_value=60, value=16)
    bitrate = st.number_input("比特率 (Mbps)", min_value=1, max_value=50, value=10)
    filename_prefix = st.text_input("文件名前缀", value="i2v/wan2.2i2v")
    
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

# 主界面布局：第一行是图像输入，第二行是提示词配置
st.markdown('<div class="upload-section">', unsafe_allow_html=True)
st.header("🖼️ 图像输入 (可选)")

# 首尾帧并列展示
img_col1, img_col2 = st.columns(2)

with img_col1:
    # 首帧图像上传
    start_image = st.file_uploader(
        "上传首帧图像",
        type=["png", "jpg", "jpeg"],
        key="start_image",
        help="视频的起始帧图像（可选）"
    )
    
    if start_image:
        st.image(start_image, caption="首帧图像", use_container_width=True)

with img_col2:
    # 尾帧图像上传
    end_image = st.file_uploader(
        "上传尾帧图像",
        type=["png", "jpg", "jpeg"],
        key="end_image",
        help="视频的结束帧图像（可选）"
    )
    
    if end_image:
        st.image(end_image, caption="尾帧图像", use_container_width=True)

st.markdown('</div>')

# 第二行：提示词配置
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="prompt-section">', unsafe_allow_html=True)
    st.header("📝 提示词配置")
    
    # 正向提示词
    positive_prompt = st.text_area(
        "正向提示词",
        value="镜头中景全身侧坐开始，镜头拉远，旋转运镜，双腿屈膝交叠，双手叉腰，切镜中景正面全身正面坐姿，镜头拉近，双腿屈膝，双手抬起摸发饰发饰，切镜近景全身侧身跪姿，旋转运镜，单膝跪地，切镜近景半身正面，单手轻触嘴唇",
        height=150,
        help="描述期望的视频内容和运镜方式"
    )
    
    # 负向提示词
    negative_prompt = st.text_area(
        "负向提示词",
        value="色彩艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG 压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走",
        height=100,
        help="描述需要避免的内容和质量问题"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # 其他参数
    video_length = st.number_input("视频长度 (帧数)", min_value=1, max_value=240, value=81, help="生成视频的总帧数")
    seed = st.number_input("随机种子", min_value=0, max_value=(1 << 53) - 1, value=807591005692968, help="控制生成的随机性")
    
    st.markdown('</div>', unsafe_allow_html=True)

# 生成按钮
st.markdown("---")
generate_btn = st.button("🚀 生成视频", type="primary")

if generate_btn:
    # 验证输入（首尾帧改为可选，只验证提示词）
    if not positive_prompt.strip():
        st.error("❌ 请输入正向提示词！")
        st.stop()
    
    # 显示进度
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">📋 准备生成视频...</div>', unsafe_allow_html=True)
    
    try:
        # 初始化客户端
        client = ComfyUIClient()
        
        # 1. 上传图像（如果已上传）
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">📤 正在处理输入...</div>', unsafe_allow_html=True)
        progress_bar.progress(10)
        
        start_filename = None
        end_filename = None
        
        if start_image:
            start_result = client.upload_image(start_image)
            start_filename = start_result["name"]
            st.info(f"首帧图像上传成功：{start_filename}")
        
        if end_image:
            end_result = client.upload_image(end_image)
            end_filename = end_result["name"]
            st.info(f"尾帧图像上传成功：{end_filename}")
        
        progress_bar.progress(20)
        
        # 2. 加载基础工作流 JSON
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">⚙️ 正在加载工作流配置...</div>', unsafe_allow_html=True)
        
        # 定义工作流路径
        default_workflow_path = r"J:\Ai_visual_processing_tools\其他\comfyui\wan2.2i2v_首尾帧.json"
        end_frame_only_workflow_path = r"J:\Ai_visual_processing_tools\其他\comfyui\wan2.2i2v_尾帧.json"
        
        # 根据输入情况选择工作流：仅当有尾帧且无首帧时，使用尾帧专用工作流
        if end_image and not start_image:
            json_path = end_frame_only_workflow_path
            st.info("检测到仅上传尾帧，已切换至尾帧专用工作流配置")
        else:
            json_path = default_workflow_path
        
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"未找到工作流 JSON 文件：{json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        progress_bar.progress(30)
        
        # 3. 动态修改工作流中的输入参数
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">🔧 正在配置工作流参数...</div>', unsafe_allow_html=True)
        
        # 修改提示词 (节点 6, 7)
        workflow["6"]["inputs"]["text"] = positive_prompt
        workflow["7"]["inputs"]["text"] = negative_prompt
        
        # 处理首帧图像节点 (68) - 仅在默认工作流中存在该节点逻辑时使用
        if json_path == default_workflow_path:
            if start_filename:
                workflow["68"]["inputs"]["image"] = start_filename
            else:
                # 如果未上传首帧且使用的是默认工作流，删除对应节点
                if "68" in workflow:
                    del workflow["68"]
                    st.warning("未上传首帧图像，已从工作流移除节点 68 (注意：若下游节点强依赖此节点，任务可能会失败)")
        # 如果使用尾帧专用工作流，则不处理节点 68（假设该工作流本身就不包含或不需要节点 68）

        # 处理尾帧图像节点 (62)
        if end_filename:
            # 确保节点存在再赋值，防止专用工作流结构不同导致报错
            if "62" in workflow:
                workflow["62"]["inputs"]["image"] = end_filename
            else:
                st.error("工作流中未找到尾帧加载节点 (62)，请检查 JSON 配置文件")
        else:
            # 如果未上传尾帧，删除对应节点
            if "62" in workflow:
                del workflow["62"]
                st.warning("未上传尾帧图像，已从工作流移除节点 62 (注意：若下游节点强依赖此节点，任务可能会失败)")
        
        # 修改采样步数和种子 
        # 节点 103: high_noise_steps (INT Constant)
        workflow["103"]["inputs"]["value"] = high_noise_steps
        # 节点 104: total_steps (INT Constant)
        workflow["104"]["inputs"]["value"] = total_steps
        
        # 节点 57: 第一阶段采样器
        workflow["57"]["inputs"]["noise_seed"] = seed
        # 节点 58: 第二阶段采样器
        workflow["58"]["inputs"]["noise_seed"] = 0
        
        # 修改视频生成参数 (节点 100)
        workflow["100"]["inputs"]["frame_rate"] = frame_rate
        workflow["100"]["inputs"]["bitrate"] = bitrate
        workflow["100"]["inputs"]["filename_prefix"] = filename_prefix
        
        # 修改 WanFirstLastFrameToVideo 节点 (节点 67) 的视频长度
        workflow["67"]["inputs"]["length"] = video_length
        
        # 应用模型路径配置
        workflow["37"]["inputs"]["unet_name"] = unet_high
        workflow["56"]["inputs"]["unet_name"] = unet_low
        workflow["38"]["inputs"]["clip_name"] = clip_model
        workflow["39"]["inputs"]["vae_name"] = vae_model
        workflow["91"]["inputs"]["lora_name"] = lora_high_noise
        workflow["92"]["inputs"]["lora_name"] = lora_low_noise
        workflow["97"]["inputs"]["lora_name"] = custom_lora

        progress_bar.progress(40)
        
        # 4. 提交工作流
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">🚀 正在提交任务到 ComfyUI...</div>', unsafe_allow_html=True)
        
        prompt_id, client_id = client.queue_prompt(workflow)
        st.success(f"任务提交成功，Prompt ID: {prompt_id}")
        
        progress_bar.progress(50)
        
        # 5. 等待执行完成
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">⏳ 正在生成视频（可能需要几分钟）...</div>', unsafe_allow_html=True)
        
        history = client.wait_for_completion(prompt_id, timeout=600)
        progress_bar.progress(80)
        
        # 6. 获取生成的视频
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">📥 正在获取生成的视频...</div>', unsafe_allow_html=True)
        
        video_filename, video_subfolder = client.get_video_from_history(prompt_id)
        
        if video_filename:
            # 获取视频数据
            video_data = client.get_image(video_filename, subfolder=video_subfolder, folder_type="output")
            
            progress_bar.progress(100)
            status_text.markdown('<div class="status-box" style="background-color: #c8e6c9;">✅ 视频生成完成！</div>', unsafe_allow_html=True)
            
            # 显示结果
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.header("🎉 生成结果")
            
            # 显示视频
            st.video(video_data)
            
            # 提供下载按钮
            download_filename = f"{filename_prefix}_{prompt_id}.mp4"
            st.download_button(
                label="📥 下载视频",
                data=video_data,
                file_name=download_filename,
                mime="video/mp4"
            )
            
            # 显示工作流信息
            with st.expander("📋 查看生成的工作流配置"):
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
    <p>💡 提示：确保 ComfyUI 服务正在运行，并且已安装所有必要的自定义节点（VHS、Wan2.2相关节点）</p>
    <p>🔧 技术支持：基于 Wan2.2 I2V 模型的首尾帧视频生成工作流</p>
</div>
""", unsafe_allow_html=True)
