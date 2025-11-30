import tkinter as tk
from tkinter import messagebox, scrolledtext
import requests
import threading
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import datetime
import os
from pathlib import Path
import sys

# ----------------------------
# 配置
# ----------------------------
# BASE_URL = "http://localhost:5500"  # 请根据实际修改
BASE_URL = "http://68.64.179.202:8000"  # 请根据实际修改
REFRESH_INTERVAL = 5000  # 5秒，单位毫秒


def resource_path(relative_path):
    """获取资源文件的真实路径（兼容 PyInstaller 打包）"""
    try:
        # PyInstaller 临时目录
        base_path = sys._MEIPASS
    except AttributeError:
        # 正常 Python 运行
        base_path = Path(__file__).parent
    return Path(base_path) / relative_path


def get_config_path(filename):
    """获取可写的配置文件路径（exe 同级或脚本同级）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / filename
    else:
        return Path(__file__).parent / filename


class AccountManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("蝙蝠账号管理系统【作者w5775213344】")
        self.root.geometry("1400x1000")
        self.root.minsize(900, 800)

        # 全局字体
        self.font_normal = ("Microsoft YaHei", 10)
        self.font_bold = ("Microsoft YaHei", 10, "bold")
        self.font_title = ("Microsoft YaHei", 14, "bold")
        self.font_card = ("Microsoft YaHei", 12, "bold")

        # 创建界面
        self.create_widgets()

        # 启动自动刷新
        self.auto_refresh_stats()
        # 设置图标
        icon_path = resource_path("logo.ico")
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception as e:
                print(f"⚠️ 无法加载图标: {e}")
        else:
            print(f"⚠️ 图标文件不存在: {icon_path}")

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        # ===== 标题 =====
        title_label = ttk.Label(
            main_frame,
            text="📊 账号统计概览",
            font=self.font_title,
            bootstyle=INFO
        )
        title_label.pack(anchor=W, pady=(0, 15))


        # ===== 统计卡片区域（三列）=====
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=X, pady=(0, 25))

        stats_frame.columnconfigure((0, 1, 2), weight=1)

        # 总计卡片
        self.total_card = self.create_stat_card(stats_frame, "总计", "0", PRIMARY)
        self.total_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        # 已使用卡片
        self.used_card = self.create_stat_card(stats_frame, "已使用", "0", DANGER)
        self.used_card.grid(row=0, column=1, padx=(0, 10), sticky="nsew")

        # 未使用卡片
        self.unused_card = self.create_stat_card(stats_frame, "未使用", "0", SUCCESS)
        self.unused_card.grid(row=0, column=2, padx=(0, 10), sticky="nsew")
        # ===== 添加账号区域 =====
        add_frame = ttk.Labelframe(main_frame, text="批量添加账号", padding=15)
        add_frame.pack(fill=X, pady=(0, 20))

        self.account_input = scrolledtext.ScrolledText(
            add_frame,
            height=8,
            font=("Consolas", 11),
            wrap=WORD,
            relief=FLAT,
            padx=10,
            pady=10
        )
        self.account_input.pack(fill=BOTH, expand=YES, pady=(0, 10))

        self.add_btn = ttk.Button(
            add_frame,
            text="添加账号",
            bootstyle=SUCCESS,
            command=self.add_accounts,
            width=15
        )
        self.add_btn.pack(side=RIGHT)

        # ===== 日志区域 =====
        log_frame = ttk.Labelframe(main_frame, text="操作日志", padding=15)
        log_frame.pack(fill=BOTH, expand=YES)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            state=DISABLED,
            font=("Consolas", 10),
            wrap=WORD,
            relief=FLAT,
            padx=10,
            pady=10
        )
        self.log_text.pack(fill=BOTH, expand=YES)


    def create_stat_card(self, parent, title, value, bootstyle):
        """创建一个有背景色的统计卡片"""
        # 创建主卡片框架（带颜色）
        card_frame = ttk.Frame(parent, bootstyle=bootstyle, padding=10)
        card_frame.grid_columnconfigure(0, weight=1)

        # 内部容器用于对齐
        inner_frame = ttk.Frame(card_frame, padding=5)
        inner_frame.pack(fill=BOTH, expand=YES)

        # 标题标签（小号字体，靠上）
        title_label = ttk.Label(
            inner_frame,
            text=title,
            font=("Microsoft YaHei", 12, "bold"),
            bootstyle=f"{bootstyle}-inverse"
        )
        title_label.pack(anchor=NW, pady=(0, 5))

        # 数值标签（大号加粗，居中）
        value_label = ttk.Label(
            inner_frame,
            text=value,
            font=("Microsoft YaHei", 20, "bold"),
            bootstyle=f"{bootstyle}-inverse"
        )
        value_label.pack(anchor=CENTER, pady=(0, 5))

        # 保存引用以便更新数值
        setattr(self, f"{title}_value_label", value_label)
        return card_frame

    def log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        full_message = f"{timestamp} {message}"
        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, full_message + "\n")
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)

    def add_accounts(self):
        raw = self.account_input.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("输入为空", "请输入至少一个账号（每行一个）", parent=self.root)
            return

        accounts = [line.strip() for line in raw.splitlines() if line.strip()]
        if not accounts:
            messagebox.showwarning("无效输入", "没有有效的账号内容", parent=self.root)
            return

        self.add_btn.config(state=DISABLED, text="处理中...")
        self.log(f"正在添加 {len(accounts)} 个账号，请稍候...")

        self.root.update_idletasks()

        threading.Thread(target=self._add_accounts_thread, args=(accounts,), daemon=True).start()

    def _add_accounts_thread(self, accounts):
        try:
            response = requests.post(f"{BASE_URL}/add_accounts", json=accounts, timeout=15)
            if response.status_code == 201:
                data = response.json()
                msg = f"成功添加 {data['message']}，跳过 {data['skipped_due_to_duplicate_or_exist']} 个重复项。"
                self.log(msg)
            else:
                error = response.json().get("error", "未知错误")
                self.log(f"添加失败: {error}")
        except Exception as e:
            self.log(f"网络异常: {str(e)}")
        finally:
            self.root.after(0, lambda: self.add_btn.config(state=NORMAL, text="添加账号"))

    def fetch_stats(self):
        threading.Thread(target=self._fetch_stats_thread, daemon=True).start()


    def _fetch_stats_thread(self):
        try:
            response = requests.get(f"{BASE_URL}/stats", timeout=5)
            if response.status_code == 200:
                data = response.json()
                total = str(data.get('total', 0))
                used = str(data.get('used', 0))
                unused = str(data.get('unused', 0))

                self.root.after(0, lambda: self.总计_value_label.config(text=total))
                self.root.after(0, lambda: self.已使用_value_label.config(text=used))
                self.root.after(0, lambda: self.未使用_value_label.config(text=unused))
            else:
                self._update_stats_error()
        except Exception:
            self._update_stats_error()

    def _update_stats_error(self):
        self.root.after(0, lambda: self.总计_value_label.config(text="--"))
        self.root.after(0, lambda: self.已使用_value_label.config(text="--"))
        self.root.after(0, lambda: self.未使用_value_label.config(text="--"))


    def auto_refresh_stats(self):
        self.fetch_stats()
        self.root.after(REFRESH_INTERVAL, self.auto_refresh_stats)


if __name__ == "__main__":
    root = ttk.Window(
        title="账号管理系统",
        themename="litera",
        size=(1000, 700),
        resizable=(True, True)
    )

    # 全局字体设置
    style = ttk.Style()
    style.configure(".", font=("Microsoft YaHei", 10))
    style.configure("TButton", font=("Microsoft YaHei", 10, "bold"))
    style.configure("TLabel", font=("Microsoft YaHei", 10))
    style.configure("TLabelframe.Label", font=("Microsoft YaHei", 11, "bold"))

    app = AccountManagerGUI(root)
    root.mainloop()