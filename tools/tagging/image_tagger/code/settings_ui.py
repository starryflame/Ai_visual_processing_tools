# AI 模型配置页面
import os
import json
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QComboBox, QGroupBox,
                             QFormLayout, QMessageBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSpinBox, QDoubleSpinBox, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 预设的模型列表
PRESET_MODELS = [
    # Qwen 系列
    "qwen3-vl:30b",
    "qwen3-vl:8b",
    "qwen2.5-vl:72b",
    "qwen2.5-vl:32b",
    "qwen2.5-vl:7b",
    "qwen3-30b-a3b",
    "qwen3-32b",
    "qwen3-14b",
    "qwen3-7b",
    # Llama 系列
    "llama-3.2-90b-vision-instruct",
    "llama-3.2-11b-vision-instruct",
    "llama-3.1-70b-instruct",
    "llama-3.1-8b-instruct",
    # InternVL 系列
    "internvl2_5-78b",
    "internvl2_5-38b",
    "internvl2_5-26b",
    "internvl2_5-8b",
    # Yi-VL 系列
    "yi-vl-34b",
    "yi-vl-6b",
    # DeepSeek 系列
    "deepseek-vl2",
    "deepseek-vl-7b",
    # 其他
    "moondream2",
    "bakllava",
    "llava-llama-3-8b",
    "phi-3.5-vision-instruct",
]

# 预设的 API 服务
PRESET_SERVICES = [
    {"name": "Ollama (本地)", "base_url": "http://127.0.0.1:11434/v1", "api_key": "ollama"},
    {"name": "vLLM (本地)", "base_url": "http://127.0.0.1:8000/v1", "api_key": "EMPTY"},
    {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "api_key": ""},
    {"name": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "api_key": ""},
    {"name": "SiliconCloud", "base_url": "https://api.siliconflow.cn/v1", "api_key": ""},
]


class SettingsUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.config = {}
        self.init_ui()
        self.load_config()
        self.load_saved_configs()

    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)

        # API 配置区域
        api_group = QGroupBox("API 配置")
        api_layout = QFormLayout()
        api_layout.setSpacing(15)

        # Base URL 输入
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("例如：http://127.0.0.1:11434/v1")
        api_layout.addRow("Base URL:", self.base_url_input)

        # API Key 输入
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("输入 API Key")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key:", self.api_key_input)

        # 显示/隐藏 API Key 按钮
        self.toggle_api_key_btn = QPushButton("显示")
        self.toggle_api_key_btn.setFixedWidth(80)
        self.toggle_api_key_btn.clicked.connect(self.toggle_api_key_visibility)
        api_layout.addRow("", self.toggle_api_key_btn)

        # 预设服务选择
        self.preset_service_combo = QComboBox()
        self.preset_service_combo.addItem("选择预设服务...")
        for service in PRESET_SERVICES:
            self.preset_service_combo.addItem(service["name"])
        self.preset_service_combo.currentIndexChanged.connect(self.on_preset_service_changed)
        api_layout.addRow("预设服务:", self.preset_service_combo)

        api_group.setLayout(api_layout)
        main_layout.addWidget(api_group)

        # 模型配置区域
        model_group = QGroupBox("模型配置")
        model_layout = QFormLayout()
        model_layout.setSpacing(15)

        # 模型选择
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItem("请选择或输入模型名称...")
        for model in PRESET_MODELS:
            self.model_combo.addItem(model)
        model_layout.addRow("模型:", self.model_combo)

        # 自动识别模型按钮
        self.auto_detect_btn = QPushButton("自动识别模型")
        self.auto_detect_btn.clicked.connect(self.auto_detect_models)
        model_layout.addRow("", self.auto_detect_btn)

        model_group.setLayout(model_layout)
        main_layout.addWidget(model_group)

        # 高级配置区域
        advanced_group = QGroupBox("高级配置")
        advanced_layout = QFormLayout()
        advanced_layout.setSpacing(15)

        # Max Tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 131072)
        self.max_tokens_spin.setValue(16384)
        self.max_tokens_spin.setSingleStep(1024)
        advanced_layout.addRow("Max Tokens:", self.max_tokens_spin)

        # Temperature
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setValue(0.3)
        self.temperature_spin.setDecimals(2)
        self.temperature_spin.setSingleStep(0.1)
        advanced_layout.addRow("Temperature:", self.temperature_spin)

        # Top P
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setValue(0.9)
        self.top_p_spin.setDecimals(2)
        self.top_p_spin.setSingleStep(0.05)
        advanced_layout.addRow("Top P:", self.top_p_spin)

        advanced_group.setLayout(advanced_layout)
        main_layout.addWidget(advanced_group)

        # 已保存的配置列表
        config_group = QGroupBox("已保存的配置")
        config_layout = QVBoxLayout()

        self.config_table = QTableWidget()
        self.config_table.setColumnCount(4)
        self.config_table.setHorizontalHeaderLabels(["配置名称", "Base URL", "模型", "操作"])
        self.config_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.config_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.config_table.setMaximumHeight(200)
        config_layout.addWidget(self.config_table)

        # 保存配置按钮
        save_config_layout = QHBoxLayout()
        self.config_name_input = QLineEdit()
        self.config_name_input.setPlaceholderText("输入配置名称...")
        self.save_config_btn = QPushButton("保存当前配置")
        self.save_config_btn.clicked.connect(self.save_current_config)
        save_config_layout.addWidget(QLabel("配置名称:"))
        save_config_layout.addWidget(self.config_name_input)
        save_config_layout.addWidget(self.save_config_btn)

        config_layout.addLayout(save_config_layout)
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # 测试连接和保存按钮
        button_layout = QHBoxLayout()
        self.test_connection_btn = QPushButton("测试连接")
        self.test_connection_btn.clicked.connect(self.test_connection)
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.save_config)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.load_config)

        button_layout.addWidget(self.test_connection_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(button_layout)
        main_layout.addStretch()

    def toggle_api_key_visibility(self):
        """切换 API Key 显示/隐藏"""
        if self.api_key_input.echoMode() == QLineEdit.Password:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
            self.toggle_api_key_btn.setText("隐藏")
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.toggle_api_key_btn.setText("显示")

    def on_preset_service_changed(self, index):
        """预设服务改变时的处理"""
        if index > 0:  # 跳过第一个提示项
            service = PRESET_SERVICES[index - 1]
            self.base_url_input.setText(service["base_url"])
            self.api_key_input.setText(service["api_key"])

    def auto_detect_models(self):
        """自动识别可用的模型"""
        base_url = self.base_url_input.text().strip()
        api_key = self.api_key_input.text().strip()

        if not base_url:
            QMessageBox.warning(self, "警告", "请先输入 Base URL")
            return

        try:
            from openai import OpenAI

            # 尝试获取模型列表
            client = OpenAI(
                api_key=api_key if api_key else "empty",
                base_url=base_url,
                timeout=10
            )

            models = client.models.list()
            model_names = [model.id for model in models.data]

            if model_names:
                # 清空现有模型列表（保留第一个提示项）
                while self.model_combo.count() > 1:
                    self.model_combo.removeItem(1)

                # 添加检测到的模型
                for model_name in model_names:
                    self.model_combo.addItem(model_name)

                QMessageBox.information(self, "成功",
                    f"检测到 {len(model_names)} 个可用模型:\n\n" +
                    "\n".join(model_names[:10]) +
                    ("\n..." if len(model_names) > 10 else ""))
            else:
                QMessageBox.warning(self, "警告", "未检测到任何模型")

        except Exception as e:
            logger.error(f"自动检测模型失败：{e}")
            QMessageBox.critical(self, "错误", f"自动检测模型失败:\n{str(e)}")

    def test_connection(self):
        """测试 API 连接"""
        base_url = self.base_url_input.text().strip()
        api_key = self.api_key_input.text().strip()
        model = self.model_combo.currentText().strip()

        if not base_url:
            QMessageBox.warning(self, "警告", "请先输入 Base URL")
            return

        if not model or model == "请选择或输入模型名称...":
            QMessageBox.warning(self, "警告", "请先选择或输入模型名称")
            return

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key if api_key else "empty",
                base_url=base_url,
                timeout=30
            )

            # 尝试获取模型信息
            response = client.models.retrieve(model)

            QMessageBox.information(self, "成功",
                f"连接成功!\n\n模型：{response.id}\nBase URL: {base_url}")

        except Exception as e:
            logger.error(f"连接测试失败：{e}")
            QMessageBox.critical(self, "错误", f"连接测试失败:\n{str(e)}")

    def save_config(self):
        """保存配置到 config.ini"""
        import configparser

        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')

        # 读取现有配置
        if os.path.exists(config_path):
            config.read(config_path, encoding='utf-8')

        # 更新配置
        if 'OLLAMA' not in config:
            config.add_section('OLLAMA')

        config.set('OLLAMA', 'api_base_url', self.base_url_input.text().strip())
        config.set('OLLAMA', 'api_key', self.api_key_input.text().strip())
        config.set('OLLAMA', 'model_name', self.model_combo.currentText().strip())
        config.set('OLLAMA', 'max_tokens', str(self.max_tokens_spin.value()))
        config.set('OLLAMA', 'temperature', str(self.temperature_spin.value()))
        config.set('OLLAMA', 'top_p', str(self.top_p_spin.value()))

        # 写入文件
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)

        QMessageBox.information(self, "成功", "配置已保存!")

        # 如果父窗口有刷新配置的方法，调用它
        if self.parent and hasattr(self.parent, 'refresh_config'):
            self.parent.refresh_config()

    def load_config(self):
        """从 config.ini 加载配置"""
        import configparser

        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')

        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')

            if 'OLLAMA' in config:
                self.base_url_input.setText(config.get('OLLAMA', 'api_base_url', fallback="http://127.0.0.1:11434/v1"))
                self.api_key_input.setText(config.get('OLLAMA', 'api_key', fallback="ollama"))
                self.model_combo.setCurrentText(config.get('OLLAMA', 'model_name', fallback="qwen3-vl:30b"))
                self.max_tokens_spin.setValue(config.getint('OLLAMA', 'max_tokens', fallback=16384))
                self.temperature_spin.setSingleStep(0.01)
                self.temperature_spin.setValue(config.getfloat('OLLAMA', 'temperature', fallback=0.3))
                self.top_p_spin.setValue(config.getfloat('OLLAMA', 'top_p', fallback=0.9))

    def save_current_config(self):
        """保存当前配置到命名配置列表"""
        config_name = self.config_name_input.text().strip()

        if not config_name:
            QMessageBox.warning(self, "警告", "请输入配置名称")
            return

        import configparser

        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')

        # 读取现有配置
        if os.path.exists(config_path):
            config.read(config_path, encoding='utf-8')

        # 保存为命名配置
        if config_name not in config:
            config.add_section(config_name)

        config.set(config_name, 'api_base_url', self.base_url_input.text().strip())
        config.set(config_name, 'api_key', self.api_key_input.text().strip())
        config.set(config_name, 'model_name', self.model_combo.currentText().strip())
        config.set(config_name, 'max_tokens', str(self.max_tokens_spin.value()))
        config.set(config_name, 'temperature', str(self.temperature_spin.value()))
        config.set(config_name, 'top_p', str(self.top_p_spin.value()))

        # 写入文件
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)

        # 刷新配置列表
        self.load_saved_configs()

        QMessageBox.information(self, "成功", f"配置 '{config_name}' 已保存!")

    def load_saved_configs(self):
        """加载已保存的配置列表"""
        import configparser

        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')

        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')

            self.config_table.setRowCount(0)

            for section in config.sections():
                if section in ['OLLAMA', 'VLLM', 'PROMPTS', 'FILTER_WORDS', 'MAX_CAPTION_LENGTH', 'PROCESSING']:
                    continue

                row = self.config_table.rowCount()
                self.config_table.insertRow(row)

                base_url = config.get(section, 'api_base_url', fallback='')
                model_name = config.get(section, 'model_name', fallback='')

                self.config_table.setItem(row, 0, QTableWidgetItem(section))
                self.config_table.setItem(row, 1, QTableWidgetItem(base_url))
                self.config_table.setItem(row, 2, QTableWidgetItem(model_name))

                # 加载按钮
                load_btn = QPushButton("加载")
                load_btn.clicked.connect(lambda checked, s=section: self.load_named_config(s))
                self.config_table.setCellWidget(row, 3, load_btn)

    def load_named_config(self, section):
        """加载命名配置"""
        import configparser

        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')

        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')

            if section in config:
                self.base_url_input.setText(config.get(section, 'api_base_url', fallback=''))
                self.api_key_input.setText(config.get(section, 'api_key', fallback=''))
                self.model_combo.setCurrentText(config.get(section, 'model_name', fallback=''))
                self.max_tokens_spin.setValue(config.getint(section, 'max_tokens', fallback=16384))
                self.temperature_spin.setValue(config.getfloat(section, 'temperature', fallback=0.3))
                self.top_p_spin.setValue(config.getfloat(section, 'top_p', fallback=0.9))

                QMessageBox.information(self, "成功", f"已加载配置 '{section}'")
