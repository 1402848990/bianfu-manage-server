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
from PJYSDK import *

# ----------------------------
# 配置
# ----------------------------
IS_TEST = True
BASE_URL = "http://localhost:5500"  # 请根据实际修改
# BASE_URL = "http://68.64.179.202:8000"  # 请根据实际修改
REFRESH_INTERVAL = 4000  # 5秒，单位毫秒
is_access = False

# 初始化 app_key 和 app_secret 在开发者后台新建软件获取
pjysdk = PJYSDK(app_key='d4kh3jjdqusv590mn8bg',
                app_secret='r8N99Iz1ityyVuDhKWI9ak2sAAPg2F02')
pjysdk.debug = False

# 心跳失败回调


def on_heartbeat_failed(hret):
    print(hret.message)
    if hret.code == 10214:
        os._exit(1)  # 退出脚本
    print("心跳失败，尝试重登...")
    login_ret = pjysdk.card_login()
    if login_ret.code == 0:
        print("重登成功")
    else:
        print(login_ret.message)  # 重登失败
        os._exit(1)  # 退出脚本


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
        global is_access
        self.root = root
        self.root.title("蝙蝠账号管理系统【作者w5775213344】")
        # self.root.title("蝙蝠账号管理系统")
        self.root.geometry("1400x1000")
        self.root.minsize(900, 800)

        # 全局字体
        self.font_normal = ("Microsoft YaHei", 10)
        self.font_bold = ("Microsoft YaHei", 10, "bold")
        self.font_title = ("Microsoft YaHei", 14, "bold")
        self.font_card = ("Microsoft YaHei", 12, "bold")

        # 授权码变量
        self.auth_code_var = tk.StringVar()
        self.auth_code_file = get_config_path("auth_code.txt")
        self.load_auth_code()

        # 创建界面
        self.create_widgets()

        # 设置图标
        icon_path = resource_path("logo.ico")
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception as e:
                print(f"⚠️ 无法加载图标: {e}")
        else:
            print(f"⚠️ 图标文件不存在: {icon_path}")

        auth_code = self.auth_code_var.get().strip()
        # global AUTH_CODE
        # AUTH_CODE = auth_code
        print("授权码:", auth_code)
        # if not auth_code:
        #     # self.log_with_color("🔒 授权码不能为空", 'red')
        #     return

        pjysdk.on_heartbeat_failed = on_heartbeat_failed  # 设置心跳失败回调函数
        mac_num = hex(uuid.getnode()).replace('0x', '').upper()
        mac_address = ':'.join(mac_num[i: i + 2] for i in range(0, 12, 2))
        print(mac_address)
        pjysdk.set_device_id(mac_address)  # 设置设备唯一ID
        pjysdk.set_card(auth_code)  # 设置卡密

        ret = pjysdk.card_login()  # 卡密登录
        # print("登录结果:", ret.code, ret.message)
        # 安全判断：ret 可能是 dict 或对象
        if isinstance(ret, dict):
            code = ret.get('code')
            message = ret.get('message', '未知错误')
        else:
            # 假设是对象
            code = getattr(ret, 'code', -1)
            message = getattr(ret, 'message', '未知错误')
        print(f"登录结果: {code} {message}")
        if code != 0:  # 登录失败
            print("❌ 登录失败")
            print(message)
            is_access = False
            # os._exit(1)  # 退出脚本
        else:
            is_access = True
            print("✅ 登录成功")
            # auth_config = pjysdk.get_card_config()

            # # 如果配置中返回了config，则更新 MAX_NUMBER  {'code': 0, 'message': 'ok', 'result': {'config': '卡密配置test'}, 'nonce': 'd4hi08oo3pjejt9hr2g0', 'sign': 'aa698d43b83db20e4e782e7cdc5d0afa'}
            # if auth_config and 'result' in auth_config:
            #     config_str = auth_config['result']['config']
            #     print(f"卡密配置: {config_str}")
            #     try:
            #         max_num = int(config_str)
            #         global MAX_NUMBER
            #         MAX_NUMBER = max_num
            #         print(f"已设置最大可用数量为: {MAX_NUMBER}")
            #     except ValueError:
            #         print("⚠️ 卡密配置无法转换为整数，保持默认值")

            # print(f"配置:{auth_config}")

        if not is_access:
            # 弹窗提示
            messagebox.showerror("错误", f"❌ 无权限，请联系微信:w5775213344")
            return

        # 启动自动刷新
        self.auto_refresh_stats()

    def load_auth_code(self):
        """从本地文件加载授权码"""
        if self.auth_code_file.exists():
            try:
                with open(self.auth_code_file, "r", encoding="utf-8") as f:
                    code = f.read().strip()
                    self.auth_code_var.set(code)
            except Exception as e:
                print(f"⚠️ 读取授权码失败: {e}")

    def save_auth_code(self, *args):
        """保存授权码到本地文件（自动触发）"""
        code = self.auth_code_var.get().strip()
        try:
            with open(self.auth_code_file, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as e:
            print(f"⚠️ 保存授权码失败: {e}")

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        # ===== 授权码输入区域 =====
        auth_frame = ttk.Frame(main_frame)
        auth_frame.pack(fill=X, pady=(0, 15))

        ttk.Label(auth_frame, text="授权码:", font=self.font_normal).pack(
            side=LEFT, padx=(0, 10))
        auth_entry = ttk.Entry(
            auth_frame,
            textvariable=self.auth_code_var,
            width=30,
            font=self.font_normal
        )
        auth_entry.pack(side=LEFT)
        self.auth_code_var.trace_add("write", self.save_auth_code)  # 自动保存

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
        self.total_card = self.create_stat_card(
            stats_frame, "总计", "0", PRIMARY)
        self.total_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        # 已使用卡片
        self.used_card = self.create_stat_card(stats_frame, "已使用", "0", DANGER)
        self.used_card.grid(row=0, column=1, padx=(0, 10), sticky="nsew")

        # 未使用卡片
        self.unused_card = self.create_stat_card(
            stats_frame, "未使用", "0", SUCCESS)
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

        # 新增：自动去重复选框 + 按钮
        btn_frame = ttk.Frame(add_frame)
        btn_frame.pack(fill=X)

        # 复选框变量
        self.disable_dedup_var = tk.BooleanVar(value=False)  # 默认不勾选 → 启用去重

        dedup_check = ttk.Checkbutton(
            btn_frame,
            text="不去重",
            variable=self.disable_dedup_var,
            bootstyle="warning"
        )
        dedup_check.pack(side=LEFT)

        self.add_btn = ttk.Button(
            btn_frame,
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
        if not is_access:
            messagebox.showerror("错误", f"❌ 无权限，请联系微信:w5775213344")
            return
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

        threading.Thread(target=self._add_accounts_thread,
                         args=(accounts,), daemon=True).start()

    def _add_accounts_thread(self, accounts):
        auth_code = self.auth_code_var.get().strip()
        host = ''

        if auth_code.startswith('sg'):
            host = 'http://38.55.193.129:8000'  # 时光
        elif IS_TEST:
            host = BASE_URL
        elif auth_code.startswith('0079'):
            host = 'http://38.55.198.178:8000'  # 0079
        elif auth_code.startswith('xg'):
            host = 'http://68.64.179.202:8000'  # 西瓜
        elif auth_code.startswith('whns'):
            host = 'http://68.64.179.234:8000'  # 我还能睡
        
        elif auth_code == 'cchppdqk24':  # 我的授权码
            host = 'http://68.64.179.202:8000'  # 西瓜

        print("使用的host:", host)
        # 获取是否禁用去重
        disable_dedup = self.disable_dedup_var.get()

        try:
            response = requests.post(
                f"{host}/add_accounts", json={
                    "accounts": accounts,
                    "disable_dedup": disable_dedup  # 新增字段
                }, timeout=15)
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
            self.root.after(0, lambda: self.add_btn.config(
                state=NORMAL, text="添加账号"))

    def fetch_stats(self):
        threading.Thread(target=self._fetch_stats_thread, daemon=True).start()

    def _fetch_stats_thread(self):
        auth_code = self.auth_code_var.get().strip()
        host = ''

        if auth_code.startswith('sg'):
            host = 'http://38.55.193.129:8000'  # 时光
        elif IS_TEST:
            host = BASE_URL
        elif auth_code.startswith('0079'):
            host = 'http://38.55.198.178:8000'  # 0079
        elif auth_code.startswith('xg'):
            host = 'http://68.64.179.202:8000'  # 西瓜
        elif auth_code.startswith('whns'):
            host = 'http://68.64.179.234:8000'  # 我还能睡

        elif auth_code == 'cchppdqk24':  # 我的授权码
            host = 'http://68.64.179.202:8000'  # 西瓜

        print("使用的host:", host)
        try:
            response = requests.get(f"{host}/stats", timeout=5)
            if response.status_code == 200:
                data = response.json()
                total = str(data.get('total', 0))
                used = str(data.get('used', 0))
                unused = str(data.get('unused', 0))

                self.root.after(
                    0, lambda: self.总计_value_label.config(text=total))
                self.root.after(
                    0, lambda: self.已使用_value_label.config(text=used))
                self.root.after(
                    0, lambda: self.未使用_value_label.config(text=unused))
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
