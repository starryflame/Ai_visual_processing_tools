import streamlit as st
import json
import os
from PIL import Image
import requests
import time
import uuid
import websocket
import traceback

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

# 页面配置
st.set_page_config(
    page_title="Qwen-Image 图像生成器",
    page_icon="🎨",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #9C27B0;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
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
        background-color: #9C27B0;
        color: white;
        font-weight: bold;
        padding: 15px;
        border-radius: 8px;
        border: none;
        font-size: 1.1rem;
    }
    .stButton>button:hover {
        background-color: #7B1FA2;
    }
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<div class="main-header">🎨 Qwen-Image 图像生成器</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">基于 Qwen-Image 2512 4 步工作流 · 快速生成高质量海报</div>', unsafe_allow_html=True)

# 侧边栏 - 参数设置
with st.sidebar:
    st.header("⚙️ 采样参数")
    
    seed = st.number_input("随机种子", min_value=0, max_value=2**31-1, value=460177615008982)
    steps = st.slider("生成步数", min_value=1, max_value=10, value=4)
    cfg = st.number_input("CFG 值", min_value=0.0, max_value=20.0, value=1.0, step=0.5)
    
    col1, col2 = st.columns(2)
    with col1:
        width = st.number_input("宽度", min_value=256, max_value=2048, value=1056)
    with col2:
        height = st.number_input("高度", min_value=256, max_value=2048, value=1584)
    
    filename_prefix = st.text_input("文件名前缀", value="QwenImage")
    
    st.markdown("---")
    if st.button("🔌 测试 ComfyUI 连接"):
        try:
            response = requests.get(f"{COMFYUI_SERVER}/system_stats", timeout=5)
            if response.status_code == 200:
                st.success("✅ ComfyUI 连接成功！")
            else:
                st.error(f"❌ 连接失败：状态码 {response.status_code}")
        except Exception as e:
            st.error(f"❌ 连接失败：{str(e)}")

# 主界面 - 提示词输入
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="prompt-section">', unsafe_allow_html=True)
    
    st.header("📝 正向提示词")
    positive_prompt = st.text_area(
        "描述要生成的图像",
        value="""卡通 3D 风格海报，欢乐明亮。背景是春日蓝天白云下的户外踏青场景：绿色草地上点缀着五彩鲜花和飞舞的蝴蝶，远处有风筝在天空飘扬，草地上摆放着野餐毯和彩色遮阳伞，伞下挂着小彩灯，营造温馨春游氛围。前景是一位卡通小朋友手持风筝线，旁边一只可爱的小兔子蹦跳跟随，画面 Q 萌治愈。

文字排版：
上方大标题（粗体活泼中文，带花朵和风筝装饰）：春日踏青 欢乐出游
副标题（英文点缀）： SPRING OUTING
中部彩色圆角框内标语：一起拥抱春天的快乐
活动亮点介绍（白色小字，居中两行）：
风筝大赛 · 野餐派对 · 花海拍照
亲子游戏 · 自然探秘 · 春游市集
底部日期与地点（现代中文字体，居中两行）：
活动时间：2025 年 4 月 12 日 活动地点：阳光花海公园""",
        height=350,
        help="详细描述要生成的图像内容，包括场景、人物、文字排版等"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="prompt-section">', unsafe_allow_html=True)
    
    st.header("🚫 负向提示词")
    negative_prompt = st.text_area(
        "描述需要避免的内容",
        value="""低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，过度光滑，画面具有 AI 感。构图混乱。文字模糊，扭曲""",
        height=150,
        help="输入不希望出现在图像中的内容"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)

# 生成按钮
st.markdown("---")
generate_btn = st.button("🚀 开始生成", type="primary")

if generate_btn:
    if not positive_prompt.strip():
        st.error("❌ 请输入正向提示词！")
        st.stop()
    
    # 显示进度
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">📋 准备生成图像...</div>', unsafe_allow_html=True)
    
    try:
        # 初始化客户端
        client = ComfyUIClient()
        
        progress_bar.progress(10)
        
        # 加载工作流 JSON
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">⚙️ 正在加载工作流配置...</div>', unsafe_allow_html=True)
        
        workflow_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "工作流",
            "Qwen-Image-2512-4 步.json"
        )
        if not os.path.exists(workflow_path):
            workflow_path = r"其他/comfyui/工作流/Qwen-Image-2512-4 步.json"
        
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"未找到工作流 JSON 文件：{workflow_path}")

        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        progress_bar.progress(40)
        
        # 配置工作流参数
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">🔧 正在配置工作流...</div>', unsafe_allow_html=True)
        
        workflow["3"]["inputs"]["seed"] = int(seed)
        workflow["3"]["inputs"]["steps"] = steps
        workflow["3"]["inputs"]["cfg"] = cfg
        workflow["58"]["inputs"]["width"] = width
        workflow["58"]["inputs"]["height"] = height
        workflow["60"]["inputs"]["filename_prefix"] = filename_prefix
        
        # 提示词配置
        for node_id in ["6"]:
            workflow[node_id]["inputs"]["text"] = positive_prompt.strip()
        
        for node_id in ["7"]:
            workflow[node_id]["inputs"]["text"] = negative_prompt.strip()
        
        progress_bar.progress(50)
        
        # 提交工作流
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">🚀 正在提交任务到 ComfyUI...</div>', unsafe_allow_html=True)
        
        prompt_id, client_id = client.queue_prompt(workflow)
        st.success(f"任务提交成功，Prompt ID: {prompt_id}")
        
        progress_bar.progress(60)
        
        # 等待执行完成
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">⏳ 正在生成图像（4 步快速模式）...</div>', unsafe_allow_html=True)
        
        history = client.wait_for_completion(prompt_id, timeout=120)
        progress_bar.progress(80)
        
        # 获取生成的图像
        status_text.markdown('<div class="status-box" style="background-color: #e3f2fd;">📥 正在获取生成的图像...</div>', unsafe_allow_html=True)
        
        if prompt_id in history:
            output = history[prompt_id].get("outputs", {})
            
            for node_id, node_data in output.items():
                if "images" in node_data:
                    for img_info in node_data["images"]:
                        filename = img_info.get("filename")
                        subfolder = img_info.get("subfolder", "")
                        
                        # 下载图像
                        response = requests.get(
                            f"{COMFYUI_SERVER}/view?filename={filename}&subfolder={subfolder}&type=output",
                            stream=True
                        )
                        response.raise_for_status()
                        
                        progress_bar.progress(100)
                        status_text.markdown('<div class="status-box" style="background-color: #c8e6c9;">✅ 图像生成完成！</div>', unsafe_allow_html=True)
                        
                        # 显示结果
                        st.markdown('<div class="result-section">', unsafe_allow_html=True)
                        st.header("🎉 生成结果")
                        
                        img = Image.open(BytesIO(response.content))
                        col_result1, col_result2 = st.columns([2, 1])
                        
                        with col_result1:
                            st.subheader("生成的图像")
                            st.image(img, use_container_width=True)
                            
                            # 下载按钮
                            download_filename = f"{filename_prefix}_{prompt_id}.png"
                            st.download_button(
                                label="📥 下载图像",
                                data=response.content,
                                file_name=download_filename,
                                mime="image/png"
                            )
                        
                        with col_result2:
                            st.subheader("生成参数")
                            st.markdown(f"**随机种子**: {seed}")
                            st.markdown(f"**生成步数**: {steps}")
                            st.markdown(f"**CFG 值**: {cfg}")
                            st.markdown(f"**图像尺寸**: {width} x {height}")
                            st.markdown(f"**Prompt ID**: `{prompt_id}`")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        break
        else:
            st.warning("⚠️ 未找到生成的图像，请检查 ComfyUI 日志")
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
    <p>💡 提示：确保 ComfyUI 服务正在运行，并且已安装 Qwen-Image 相关自定义节点</p>
    <p>🔧 基于 Qwen-Image Lightning 4 步快速生成工作流</p>
</div>
""", unsafe_allow_html=True)
