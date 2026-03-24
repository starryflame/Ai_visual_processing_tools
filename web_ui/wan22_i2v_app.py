import streamlit as st
import json
import os
from PIL import Image
import requests
from io import BytesIO
import base64
import time

# 页面配置
st.set_page_config(
    page_title="Wan2.2 首尾帧视频生成",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
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
    custom_lora = st.text_input("自定义运镜 LoRA", value="自创\\wan2.2\\高噪\\i2v\\运镜 3-22.safetensors")
    
    # 视频输出设置
    st.subheader("视频输出")
    frame_rate = st.number_input("帧率", min_value=1, max_value=60, value=16)
    bitrate = st.number_input("比特率 (Mbps)", min_value=1, max_value=50, value=10)
    filename_prefix = st.text_input("文件名前缀", value="i2v/wan2.2i2v")

# 主界面分为两列
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.header("🖼️ 图像输入")
    
    # 首帧图像上传
    start_image = st.file_uploader(
        "上传首帧图像",
        type=["png", "jpg", "jpeg"],
        key="start_image",
        help="视频的起始帧图像"
    )
    
    if start_image:
        st.image(start_image, caption="首帧图像", use_container_width=True)
    
    # 尾帧图像上传
    end_image = st.file_uploader(
        "上传尾帧图像",
        type=["png", "jpg", "jpeg"],
        key="end_image",
        help="视频的结束帧图像"
    )
    
    if end_image:
        st.image(end_image, caption="尾帧图像", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
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
        value="色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG 压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走",
        height=100,
        help="描述需要避免的内容和质量问题"
    )
    
    # 其他参数
    video_length = st.number_input("视频长度 (帧数)", min_value=1, max_value=240, value=81, help="生成视频的总帧数")
    seed = st.number_input("随机种子", min_value=0, max_value=(1 << 53) - 1, value=807591005692968, help="控制生成的随机性")
    
    st.markdown('</div>', unsafe_allow_html=True)

# 生成按钮
st.markdown("---")
generate_btn = st.button("🚀 生成视频", type="primary")

if generate_btn:
    # 验证输入
    if not start_image or not end_image:
        st.error("❌ 请上传首帧和尾帧图像！")
        st.stop()
    
    if not positive_prompt.strip():
        st.error("❌ 请输入正向提示词！")
        st.stop()
    
    # 显示进度
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 构建 ComfyUI 工作流
        workflow = {
            "6": {
                "inputs": {
                    "text": positive_prompt,
                    "clip": ["38", 0]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Positive Prompt)"}
            },
            "7": {
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["38", 0]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Negative Prompt)"}
            },
            "37": {
                "inputs": {
                    "unet_name": unet_high,
                    "weight_dtype": "fp8_e4m3fn"
                },
                "class_type": "UNETLoader",
                "_meta": {"title": "UNet 加载器"}
            },
            "38": {
                "inputs": {
                    "clip_name": clip_model,
                    "type": "wan",
                    "device": "default"
                },
                "class_type": "CLIPLoader",
                "_meta": {"title": "加载 CLIP"}
            },
            "39": {
                "inputs": {
                    "vae_name": vae_model
                },
                "class_type": "VAELoader",
                "_meta": {"title": "加载 VAE"}
            },
            "54": {
                "inputs": {
                    "shift": 5,
                    "model": ["97", 0]
                },
                "class_type": "ModelSamplingSD3",
                "_meta": {"title": "采样算法（SD3）"}
            },
            "55": {
                "inputs": {
                    "shift": 5,
                    "model": ["92", 0]
                },
                "class_type": "ModelSamplingSD3",
                "_meta": {"title": "采样算法（SD3）"}
            },
            "56": {
                "inputs": {
                    "unet_name": unet_low,
                    "weight_dtype": "fp8_e4m3fn"
                },
                "class_type": "UNETLoader",
                "_meta": {"title": "UNet 加载器"}
            },
            "57": {
                "inputs": {
                    "add_noise": "enable",
                    "noise_seed": seed,
                    "steps": total_steps,
                    "cfg": 1,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "start_at_step": 0,
                    "end_at_step": high_noise_steps,
                    "return_with_leftover_noise": "enable",
                    "model": ["54", 0],
                    "positive": ["67", 0],
                    "negative": ["67", 1],
                    "latent_image": ["67", 2]
                },
                "class_type": "KSamplerAdvanced",
                "_meta": {"title": "K 采样器（高级）"}
            },
            "58": {
                "inputs": {
                    "add_noise": "disable",
                    "noise_seed": 0,
                    "steps": total_steps,
                    "cfg": 1,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "start_at_step": high_noise_steps,
                    "end_at_step": 10000,
                    "return_with_leftover_noise": "disable",
                    "model": ["55", 0],
                    "positive": ["67", 0],
                    "negative": ["67", 1],
                    "latent_image": ["57", 0]
                },
                "class_type": "KSamplerAdvanced",
                "_meta": {"title": "K 采样器（高级）"}
            },
            "67": {
                "inputs": {
                    "width": 1024,
                    "height": 1024,
                    "length": video_length,
                    "batch_size": 1,
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "vae": ["39", 0],
                    "start_image": ["68", 0],
                    "end_image": ["105", 0]
                },
                "class_type": "WanFirstLastFrameToVideo",
                "_meta": {"title": "Wan 首尾帧视频"}
            },
            "91": {
                "inputs": {
                    "lora_name": lora_high_noise,
                    "strength_model": 1,
                    "model": ["37", 0]
                },
                "class_type": "LoraLoaderModelOnly",
                "_meta": {"title": "LoRA 加载器（仅模型）"}
            },
            "92": {
                "inputs": {
                    "lora_name": lora_low_noise,
                    "strength_model": 1,
                    "model": ["56", 0]
                },
                "class_type": "LoraLoaderModelOnly",
                "_meta": {"title": "LoRA 加载器（仅模型）"}
            },
            "97": {
                "inputs": {
                    "lora_name": custom_lora,
                    "strength_model": 1,
                    "model": ["91", 0]
                },
                "class_type": "LoraLoaderModelOnly",
                "_meta": {"title": "LoRA 加载器（仅模型）"}
            },
            "100": {
                "inputs": {
                    "frame_rate": frame_rate,
                    "loop_count": 0,
                    "filename_prefix": filename_prefix,
                    "format": "video/nvenc_h264-mp4",
                    "pix_fmt": "yuv420p",
                    "bitrate": bitrate,
                    "megabit": True,
                    "save_metadata": True,
                    "pingpong": False,
                    "save_output": True,
                    "images": ["8", 0]
                },
                "class_type": "VHS_VideoCombine",
                "_meta": {"title": "Video Combine 🎥🅥🅗🅢"}
            },
            "103": {
                "inputs": {"value": high_noise_steps},
                "class_type": "INTConstant",
                "_meta": {"title": "INT Constant"}
            },
            "104": {
                "inputs": {"value": total_steps},
                "class_type": "INTConstant",
                "_meta": {"title": "INT Constant"}
            }
        }
        
        # 模拟生成过程
        status_text.text("🔄 正在处理图像...")
        progress_bar.progress(20)
        time.sleep(1)
        
        status_text.text("🎨 正在加载模型...")
        progress_bar.progress(40)
        time.sleep(1)
        
        status_text.text("🎬 正在生成视频...")
        progress_bar.progress(60)
        time.sleep(2)
        
        status_text.text("✨ 正在合成最终结果...")
        progress_bar.progress(80)
        time.sleep(1)
        
        progress_bar.progress(100)
        status_text.text("✅ 生成完成！")
        
        # 显示结果
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.header("🎉 生成结果")
        
        # 这里应该调用 ComfyUI API 获取实际结果
        # 由于是示例，我们显示一个占位符
        st.success("视频生成成功！在实际部署中，这里会显示生成的视频文件。")
        
        # 显示工作流信息
        with st.expander("📋 查看生成的工作流配置"):
            st.json(workflow)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"❌ 生成失败：{str(e)}")
        progress_bar.empty()
        status_text.empty()

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>💡 提示：确保 ComfyUI 服务正在运行，并且已安装所有必要的自定义节点</p>
    <p>🔧 技术支持：基于 Wan2.2 I2V 模型的首尾帧视频生成工作流</p>
</div>
""", unsafe_allow_html=True)