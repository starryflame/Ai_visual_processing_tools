#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图像相似度自动配对工具 - 入口"""

import tkinter as tk
from config import DARK_BG
from gui import GUI


def main():
    root = tk.Tk()
    root.config(bg=DARK_BG)
    app = GUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
