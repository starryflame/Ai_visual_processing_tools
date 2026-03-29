import random
import streamlit as st
import json
import os
from PIL import Image
import requests
import time
import uuid
import websocket
import traceback
from io import BytesIO

# ComfyUI 服务器配置
COMFYUI_SERVER = os.getenv("COMFYUI_SERVER", "http://127.0.0.1:8188")
os.environ["PYTHONIOENCODING"] = "utf-8"


class ComfyUIClient:
    """ComfyUI API 客户端封装"""

    def __init__(self, server_address=COMFYUI_SERVER):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())

    def queue_prompt(self, workflow):
        """提交工作流到 ComfyUI 队列"""
        try:
            payload = {
                "prompt": workflow,
                "client_id": self.client_id,
            }
            response = requests.post(
                f"{self.server_address}/prompt",
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
                f"{self.server_address}/history/{prompt_id}",
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


def load_workflow(workflow_type):
    """加载对应的工作流 JSON 文件"""
    workflow_paths = {
        "single": os.path.join(
            os.path.dirname(__file__),
            "..",
            "工作流",
            "单图编辑.json"
        ),
        "double": os.path.join(
            os.path.dirname(__file__),
            "..",
            "工作流",
            "双图编辑.json"
        ),
        "triple": os.path.join(
            os.path.dirname(__file__),
            "..",
            "工作流",
            "三图编辑.json"
        )
    }

    workflow_path = workflow_paths.get(workflow_type)

    if not workflow_path or not os.path.exists(workflow_path):
        # 尝试相对路径
        alt_path = rf"其他/comfyui/工作流/qwen_edit_aio_{workflow_type}图编辑.json"
        if os.path.exists(alt_path):
            workflow_path = alt_path
        else:
            raise FileNotFoundError(f"未找到工作流 JSON 文件：{workflow_path}")

    with open(workflow_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def upload_image_to_comfyui(image, filename_prefix):
    """上传图片到 ComfyUI 临时目录"""
    server = COMFYUI_SERVER.replace("http://", "").replace("https://", "")
    
    # 生成唯一文件名
    unique_filename = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.png"
    
    try:
        response = requests.post(
            f"http://{server}/upload/image",
            files={"image": (unique_filename, image.getvalue(), "image/png")},
            timeout=30
        )
        response.raise_for_status()
        return unique_filename
    except Exception as e:
        st.error(f"上传图片失败：{str(e)}")
        raise


st.set_page_config(
    page_title="Qwen-Image 多模式编辑器",
    page_icon="🎨",
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
    .upload-section, .prompt-section {
        background-color: #f5f5f5;
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
    .mode-selector {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .mode-card {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 2px solid transparent;
    }
    .mode-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .mode-card.active {
        border-color: #1E88E5;
        background-color: #e3f2fd;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🎨 Qwen-Image 多模式图像编辑器</div>', unsafe_allow_html=True)

# 侧边栏设置
with st.sidebar:
    st.header("⚙️ 高级设置")
    
    if "current_seed" not in st.session_state:
        st.session_state.current_seed = int(time.time()) % (2**53)
    
    st.subheader("采样设置")
    seed = st.number_input(
        "随机种子", 
        min_value=0, 
        max_value=2**53-1, 
        value=st.session_state.current_seed,
        help="控制生成结果的随机性"
    )
    
    if st.button("🎲 刷新种子", key="refresh_seed"):
        st.session_state.current_seed = random.randint(0, 2**53 - 1)
        st.rerun()
    
 
    col1, col2 = st.columns(2)
    with col1:
        width = st.number_input("宽度", min_value=256, max_value=2048, value=1056)
    with col2:
        height = st.number_input("高度", min_value=256, max_value=2048, value=1584)
    
    filename_prefix = st.text_input("文件名前缀", value="QwenEdit")
    
    st.markdown("---")
    st.subheader("🔌 连接测试")
    if st.button("测试 ComfyUI 连接"):
        try:
            response = requests.get(f"{COMFYUI_SERVER}/system_stats", timeout=5)
            if response.status_code == 200:
                st.success("✅ ComfyUI 连接成功！")
            else:
                st.error(f"❌ 连接失败：状态码 {response.status_code}")
        except Exception as e:
            st.error(f"❌ 连接失败：{str(e)}")

# 模式选择器
st.markdown('<div class="mode-selector">', unsafe_allow_html=True)
selected_mode = st.radio(
    "🎯 选择编辑模式",
    ["单图编辑", "双图编辑", "三图编辑"],
    index=0,
    help="根据输入图片数量选择合适的编辑模式"
)

mode_to_type = {
    "单图编辑": "single",
    "双图编辑": "double",
    "三图编辑": "triple"
}
workflow_type = mode_to_type[selected_mode]
st.markdown('</div>', unsafe_allow_html=True)

# 根据模式显示不同的图片上传区域
st.header(f"📷 {selected_mode}")

uploaded_images = []
image_filenames = []

if selected_mode == "单图编辑":
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("上传图片", type=["png", "jpg", "jpeg"], key="single_image")
    if uploaded_file:
        uploaded_images.append(uploaded_file)
        image_filenames.append(None)  # ComfyUI 会生成唯一文件名
    st.markdown('</div>', unsafe_allow_html=True)

elif selected_mode == "双图编辑":
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        uploaded_file1 = st.file_uploader("图片 1（原图）", type=["png", "jpg", "jpeg"], key="double_image_1")
        if uploaded_file1:
            uploaded_images.append(uploaded_file1)
            image_filenames.append(None)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        uploaded_file2 = st.file_uploader("图片 2（参考图）", type=["png", "jpg", "jpeg"], key="double_image_2")
        if uploaded_file2:
            uploaded_images.append(uploaded_file2)
            image_filenames.append(None)
        st.markdown('</div>', unsafe_allow_html=True)

elif selected_mode == "三图编辑":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        uploaded_file1 = st.file_uploader("图片 1", type=["png", "jpg", "jpeg"], key="triple_image_1")
        if uploaded_file1:
            uploaded_images.append(uploaded_file1)
            image_filenames.append(None)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        uploaded_file2 = st.file_uploader("图片 2", type=["png", "jpg", "jpeg"], key="triple_image_2")
        if uploaded_file2:
            uploaded_images.append(uploaded_file2)
            image_filenames.append(None)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        uploaded_file3 = st.file_uploader("图片 3", type=["png", "jpg", "jpeg"], key="triple_image_3")
        if uploaded_file3:
            uploaded_images.append(uploaded_file3)
            image_filenames.append(None)
        st.markdown('</div>', unsafe_allow_html=True)

# 提示词输入区域
st.header("📝 编辑指令")
prompt = st.text_area(
    "请输入图像编辑指令",
    value="让图 1 的人物穿上图 2 的衣服",
    height=150,
    help="描述你想要对图像进行的修改"
)

# 生成按钮
st.markdown("---")
generate_btn = st.button("🚀 开始编辑", type="primary")

if generate_btn:
    if not prompt.strip():
        st.error("❌ 请输入编辑指令！")
        st.stop()
    
    if len(uploaded_images) == 0:
        st.error(f"❌ {selected_mode}需要至少一张图片！")
        st.stop()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        client = ComfyUIClient()
        progress_bar.progress(10)
        
        # 加载工作流
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">⚙️ 正在加载工作流配置...</div>', unsafe_allow_html=True)
        workflow = load_workflow(workflow_type)
        progress_bar.progress(40)
        
        # 上传图片到 ComfyUI
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">📤 正在上传图片...</div>', unsafe_allow_html=True)
        uploaded_filenames = []
        for i, img_file in enumerate(uploaded_images):
            filename = upload_image_to_comfyui(img_file, f"{filename_prefix}_{selected_mode}_img{i+1}")
            uploaded_filenames.append(filename)
            st.info(f"✅ 图片 {i+1} 上传成功：{filename}")
        progress_bar.progress(50)
        
        # 配置工作流参数
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">🔧 正在配置工作流...</div>', unsafe_allow_html=True)
        
        # 设置种子、步数等通用参数
        for node_id in ["4"]:  # Seed 节点
            if "seed" in workflow.get(node_id, {}).get("inputs", {}):
                workflow[node_id]["inputs"]["seed"] = int(seed)
        
        
        # 设置图片输入（LoadImage 节点）
        load_image_nodes = ["12", "13", "23"]  # 根据工作流中的 LoadImage 节点 ID
        for i, node_id in enumerate(load_image_nodes):
            if node_id in workflow and i < len(uploaded_filenames):
                workflow[node_id]["inputs"]["image"] = uploaded_filenames[i]
        
        # 设置提示词（TextEncodeQwenImageEditPlusAdvance_lrzjason 节点）
        for node_id, value in [("8", prompt.strip())]:
            if node_id in workflow:
                workflow[node_id]["inputs"]["prompt"] = value
        
        progress_bar.progress(60)
        
        # 提交工作流
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">🚀 正在提交任务到 ComfyUI...</div>', unsafe_allow_html=True)
        prompt_id, client_id = client.queue_prompt(workflow)
        st.success(f"✅ 任务提交成功，Prompt ID: {prompt_id}")
        
        progress_bar.progress(70)
        
        # 等待执行完成
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">⏳ 正在生成图像...</div>', unsafe_allow_html=True)
        history = client.wait_for_completion(prompt_id, timeout=180)
        progress_bar.progress(85)
        
        # 获取生成的图像
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">📥 正在获取生成结果...</div>', unsafe_allow_html=True)
        
        if prompt_id in history:
            output = history[prompt_id].get("outputs", {})
            
            for node_id, node_data in output.items():
                if "images" in node_data:
                    for img_info in node_data["images"]:
                        filename = img_info.get("filename")
                        subfolder = img_info.get("subfolder", "")
                        
                        response = requests.get(
                            f"{COMFYUI_SERVER}/view?filename={filename}&subfolder={subfolder}&type=output",
                            stream=True
                        )
                        response.raise_for_status()
                        
                        progress_bar.progress(100)
                        status_text.markdown('<div class="status-box" style="background-color: #c8e6c9;">✅ 图像编辑完成！</div>', unsafe_allow_html=True)
                        
                        st.markdown('<div class="result-section">', unsafe_allow_html=True)
                        st.header("🎉 编辑结果")
                        
                        img = Image.open(BytesIO(response.content))
                        col_result1, col_result2 = st.columns([2, 1])
                        
                        with col_result1:
                            st.subheader("生成的图像")
                            max_height = 800
                            img_width, img_height = img.size
                            if img_height > max_height:
                                scale_factor = max_height / img_height
                                new_width = int(img_width * scale_factor)
                                st.image(img, width=new_width)
                            else:
                                st.image(img, use_container_width=True)
                            
                            download_filename = f"{filename_prefix}_{selected_mode}_{prompt_id}.png"
                            st.download_button(
                                label="📥 下载图像",
                                key=f"download_{prompt_id}",
                                data=response.content,
                                file_name=download_filename,
                                mime="image/png"
                            )
                        
                        with col_result2:
                            st.subheader("编辑参数")
                            st.markdown(f"**模式**: {selected_mode}")
                            st.markdown(f"**随机种子**: {seed}")
                            st.markdown(f"**Prompt ID**: `{prompt_id}`")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        new_seed = random.randint(0, 2**53 - 1)
                        st.session_state.current_seed = new_seed
                        break
        else:
            st.warning("⚠️ 未找到生成的图像，请检查 ComfyUI 日志")
            with st.expander("📋 查看执行历史"):
                st.json(history)
    
    except Exception as e:
        st.error(f"❌ 编辑失败：{str(e)}")
        progress_bar.progress(0)
        status_text.markdown('<div class="status-box" style="background-color: #ffcdd2;">❌ 编辑失败！</div>', unsafe_allow_html=True)
        with st.expander("🔍 详细错误信息"):
            st.code(traceback.format_exc(), language="python")

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>💡 提示：确保 ComfyUI 服务正在运行，并且已安装 Qwen-Image 相关自定义节点</p>
    <p>🔧 支持单图、双图、三图三种编辑模式</p>
</div>
""", unsafe_allow_html=True)
