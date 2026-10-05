#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双面板图片配对工具 - 主入口
"""

import tkinter as tk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from config import DARK_BG
from gui import ImagePairToolGUI


def main():
    """主函数"""
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    root.config(bg=DARK_BG)

    app = ImagePairToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
