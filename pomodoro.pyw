"""
番茄钟 (Pomodoro Timer) - Windows 桌面应用
Python 3 + Tkinter，零额外依赖
双击运行即可使用
"""

import tkinter as tk
from tkinter import ttk, messagebox
import winsound
import threading
import time

# ── 配置 ──────────────────────────────────────────────
WORK_MIN = 25          # 工作时间（分钟）
SHORT_BREAK_MIN = 5    # 短休息时间（分钟）
LONG_BREAK_MIN = 15    # 长休息时间（分钟）
LONG_BREAK_INTERVAL = 4  # 每完成 N 个番茄后进入长休息

# 颜色主题
COLOR_BG = "#1E1E2E"           # 深色背景
COLOR_SURFACE = "#2B2B3D"      # 卡片/面板色
COLOR_TEXT = "#E0E0E0"         # 主文字
COLOR_TEXT_SECONDARY = "#8888A0"  # 次要文字
COLOR_TOMATO = "#E74C3C"       # 番茄红 - 工作模式
COLOR_GREEN = "#27AE60"        # 绿色 - 短休息
COLOR_BLUE = "#3498DB"         # 蓝色 - 长休息
COLOR_BTN_BG = "#3B3B50"       # 按钮背景
COLOR_BTN_HOVER = "#4A4A62"    # 按钮悬停
COLOR_PROGRESS_BG = "#3B3B50"  # 进度条背景


class PomodoroApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🍅 番茄钟")
        self.root.geometry("420x540")
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)

        # 窗口居中
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 420) // 2
        y = (sh - 540) // 2
        self.root.geometry(f"+{x}+{y}")

        # 置顶
        self.topmost = tk.BooleanVar(value=True)
        self.root.wm_attributes("-topmost", True)

        # ── 状态变量 ──
        self.mode = "work"                # work / short_break / long_break
        self.mode_durations = {
            "work": WORK_MIN * 60,
            "short_break": SHORT_BREAK_MIN * 60,
            "long_break": LONG_BREAK_MIN * 60,
        }
        self.remaining = self.mode_durations["work"]  # 剩余秒数
        self.total = self.mode_durations["work"]      # 当前模式总秒数
        self.running = False
        self.paused = False
        self.session_count = 0            # 已完成番茄数
        self.timer_id = None

        # ── 构建界面 ──
        self._build_ui()

        # ── 窗口关闭事件 ──
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ══════════════════════════════════════════════════════
    #  UI 构建
    # ══════════════════════════════════════════════════════

    def _build_ui(self):
        # ── 主容器 ──
        main = tk.Frame(self.root, bg=COLOR_BG)
        main.pack(fill="both", expand=True, padx=24, pady=16)

        # ── 标题行 ──
        title_frame = tk.Frame(main, bg=COLOR_BG)
        title_frame.pack(fill="x", pady=(0, 8))

        self.title_label = tk.Label(
            title_frame, text="🍅 番茄钟",
            font=("Segoe UI", 18, "bold"),
            fg=COLOR_TOMATO, bg=COLOR_BG
        )
        self.title_label.pack(side="left")

        # 置顶切换
        pin_frame = tk.Frame(title_frame, bg=COLOR_BG)
        pin_frame.pack(side="right")

        self.pin_btn = tk.Label(
            pin_frame, text="📌",
            font=("Segoe UI", 14),
            fg=COLOR_TOMATO, bg=COLOR_BG,
            cursor="hand2"
        )
        self.pin_btn.pack(side="right")
        self.pin_btn.bind("<Button-1>", self._toggle_topmost)

        # ── 会话计数 ──
        counter_frame = tk.Frame(main, bg=COLOR_BG)
        counter_frame.pack(fill="x", pady=(0, 12))

        self.counter_label = tk.Label(
            counter_frame,
            text=f"已完成: {self.session_count} 个番茄",
            font=("Segoe UI", 11),
            fg=COLOR_TEXT_SECONDARY, bg=COLOR_BG
        )
        self.counter_label.pack(side="left")

        # 番茄小图标
        self.tomato_icons = tk.Label(
            counter_frame, text="",
            font=("Segoe UI", 12),
            fg=COLOR_TOMATO, bg=COLOR_BG
        )
        self.tomato_icons.pack(side="right")
        self._update_tomato_icons()

        # ── 计时器圆盘面板 ──
        timer_panel = tk.Frame(main, bg=COLOR_SURFACE, highlightthickness=0)
        timer_panel.pack(fill="x", pady=(0, 12), ipady=30)

        # 大号倒计时
        self.timer_label = tk.Label(
            timer_panel,
            text=self._fmt_time(self.remaining),
            font=("Consolas", 56, "bold"),
            fg=COLOR_TEXT, bg=COLOR_SURFACE
        )
        self.timer_label.pack()

        # 模式标签
        self.mode_label = tk.Label(
            timer_panel,
            text="专注工作",
            font=("Segoe UI", 12),
            fg=COLOR_TOMATO, bg=COLOR_SURFACE
        )
        self.mode_label.pack(pady=(0, 4))

        # ── 进度条 ──
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Pomodoro.Horizontal.TProgressbar",
            troughcolor=COLOR_PROGRESS_BG,
            background=COLOR_TOMATO,
            darkcolor=COLOR_TOMATO,
            lightcolor=COLOR_TOMATO,
            bordercolor=COLOR_SURFACE,
            thickness=8,
        )

        self.progress = ttk.Progressbar(
            main,
            style="Pomodoro.Horizontal.TProgressbar",
            mode="determinate",
            maximum=self.total,
            value=self.total,
        )
        self.progress.pack(fill="x", pady=(0, 16))

        # ── 模式按钮 ──
        mode_frame = tk.Frame(main, bg=COLOR_BG)
        mode_frame.pack(fill="x", pady=(0, 12))

        self.btn_work = self._make_mode_btn(mode_frame, "🍅 工作", COLOR_TOMATO, "work")
        self.btn_work.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self._set_btn_active(self.btn_work, COLOR_TOMATO)

        self.btn_short = self._make_mode_btn(mode_frame, "☕ 短休", COLOR_GREEN, "short_break")
        self.btn_short.pack(side="left", expand=True, fill="x", padx=2)

        self.btn_long = self._make_mode_btn(mode_frame, "🌿 长休", COLOR_BLUE, "long_break")
        self.btn_long.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # ── 控制按钮 ──
        ctrl_frame = tk.Frame(main, bg=COLOR_BG)
        ctrl_frame.pack(fill="x", pady=(0, 12))

        self.btn_start = tk.Button(
            ctrl_frame,
            text="▶  开 始",
            font=("Segoe UI", 14, "bold"),
            fg="white", bg=COLOR_TOMATO,
            activeforeground="white", activebackground="#C0392B",
            relief="flat", cursor="hand2",
            padx=20, pady=10,
            command=self._toggle_start_pause,
        )
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_reset = tk.Button(
            ctrl_frame,
            text="↺  重 置",
            font=("Segoe UI", 14, "bold"),
            fg=COLOR_TEXT, bg=COLOR_BTN_BG,
            activeforeground=COLOR_TEXT, activebackground=COLOR_BTN_HOVER,
            relief="flat", cursor="hand2",
            padx=20, pady=10,
            command=self._reset,
        )
        self.btn_reset.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # ── 提示文字 ──
        hint = tk.Label(
            main,
            text="每完成 4 个番茄进入一次长休息",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_SECONDARY, bg=COLOR_BG
        )
        hint.pack(side="bottom", pady=(4, 0))

    def _make_mode_btn(self, parent, text, active_color, mode):
        """创建模式切换按钮"""
        btn = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 11),
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_BTN_BG,
            cursor="hand2",
            padx=8, pady=6,
        )
        btn._active_color = active_color
        btn._mode = mode
        btn.bind("<Button-1>", lambda e: self._switch_mode(mode))
        return btn

    def _set_btn_active(self, btn, color):
        """设置按钮为选中状态"""
        btn.configure(fg="white", bg=color)

    def _set_btn_inactive(self, btn):
        """设置按钮为未选中状态"""
        btn.configure(fg=COLOR_TEXT_SECONDARY, bg=COLOR_BTN_BG)

    # ══════════════════════════════════════════════════════
    #  核心逻辑
    # ══════════════════════════════════════════════════════

    def _switch_mode(self, mode):
        """切换工作/休息模式"""
        was_running = self.running and not self.paused

        if was_running:
            # 运行中切换：先暂停
            self._pause()

        self.mode = mode
        self.remaining = self.mode_durations[mode]
        self.total = self.mode_durations[mode]

        # 更新 UI
        self.timer_label.configure(text=self._fmt_time(self.remaining))
        self.progress.configure(maximum=self.total, value=self.total)

        # 更新模式按钮样式
        colors = {"work": COLOR_TOMATO, "short_break": COLOR_GREEN, "long_break": COLOR_BLUE}
        labels = {"work": "专注工作", "short_break": "短休息", "long_break": "长休息"}
        buttons = {"work": self.btn_work, "short_break": self.btn_short, "long_break": self.btn_long}

        for m, btn in buttons.items():
            self._set_btn_inactive(btn)

        active_color = colors[mode]
        self._set_btn_active(buttons[mode], active_color)

        # 更新模式标签和进度条颜色
        self.mode_label.configure(text=labels[mode], fg=active_color)
        style = ttk.Style()
        style.configure(
            "Pomodoro.Horizontal.TProgressbar",
            background=active_color,
            darkcolor=active_color,
            lightcolor=active_color,
        )

        # 更新开始按钮颜色和文字
        self.btn_start.configure(bg=active_color, activebackground=self._darken(active_color))

        if was_running:
            self.btn_start.configure(text="▶  继 续")
            self._mode_btns_enable(False)
        else:
            self.btn_start.configure(text="▶  开 始")
            self._mode_btns_enable(True)

    def _toggle_start_pause(self):
        """开始 / 暂停"""
        if not self.running:
            self._start()
        elif not self.paused:
            self._pause()
        else:
            self._resume()

    def _start(self):
        """开始计时"""
        self.running = True
        self.paused = False
        self.btn_start.configure(text="⏸  暂 停")

        # 禁用模式切换（运行中不允许切换模式）
        self._mode_btns_enable(False)

        self._tick()

    def _pause(self):
        """暂停"""
        self.paused = True
        self.btn_start.configure(text="▶  继 续")
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

    def _resume(self):
        """继续"""
        self.paused = False
        self.btn_start.configure(text="⏸  暂 停")
        self._tick()

    def _reset(self):
        """重置当前会话"""
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

        self.running = False
        self.paused = False
        self.remaining = self.mode_durations[self.mode]
        self.total = self.mode_durations[self.mode]

        self.timer_label.configure(text=self._fmt_time(self.remaining))
        self.progress.configure(value=self.total)
        self.btn_start.configure(text="▶  开 始")

        active_color = self._current_color()
        self.btn_start.configure(bg=active_color, activebackground=self._darken(active_color))
        self._mode_btns_enable(True)

    def _tick(self):
        """每秒回调"""
        if self.paused or not self.running:
            return

        if self.remaining > 0:
            self.remaining -= 1
            self.timer_label.configure(text=self._fmt_time(self.remaining))
            self.progress.configure(value=self.remaining)
            self.timer_id = self.root.after(1000, self._tick)
        else:
            # 时间到
            self._timer_done()

    def _timer_done(self):
        """计时完成"""
        self.running = False
        self.paused = False
        self.timer_id = None

        # 播放提示音（在后台线程中播放，避免阻塞 UI）
        threading.Thread(target=self._play_alarm, daemon=True).start()

        # 弹窗
        titles = {"work": "🍅 时间到！", "short_break": "☕ 休息结束", "long_break": "🌿 长休息结束"}
        messages = {
            "work": "一个番茄完成！休息一下吧～",
            "short_break": "短休息结束，继续加油！",
            "long_break": "长休息结束，精力充沛了吧！",
        }

        self.root.after(100, lambda: messagebox.showinfo(
            titles.get(self.mode, "时间到"),
            messages.get(self.mode, "计时结束")
        ))

        if self.mode == "work":
            # 完成一个番茄
            self.session_count += 1
            self.counter_label.configure(text=f"已完成: {self.session_count} 个番茄")
            self._update_tomato_icons()

            # 判断下一个模式
            if self.session_count % LONG_BREAK_INTERVAL == 0:
                self._switch_mode("long_break")
            else:
                self._switch_mode("short_break")
        else:
            # 休息结束，切换到工作模式
            self._switch_mode("work")

        self.btn_start.configure(text="▶  开 始")
        active_color = self._current_color()
        self.btn_start.configure(bg=active_color, activebackground=self._darken(active_color))
        self._mode_btns_enable(True)

    def _play_alarm(self):
        """播放提示音（Windows Beep）"""
        try:
            # 三段短促 Beep
            for _ in range(3):
                winsound.Beep(880, 200)
                time.sleep(0.15)
                winsound.Beep(1100, 300)
                time.sleep(0.1)
        except Exception:
            pass  # 某些系统可能不支持 Beep

    # ══════════════════════════════════════════════════════
    #  辅助方法
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _fmt_time(seconds):
        """格式化为 MM:SS"""
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def _current_color(self):
        """当前模式的颜色"""
        colors = {"work": COLOR_TOMATO, "short_break": COLOR_GREEN, "long_break": COLOR_BLUE}
        return colors.get(self.mode, COLOR_TOMATO)

    @staticmethod
    def _darken(hex_color, factor=0.85):
        """颜色加深"""
        hex_color = hex_color.lstrip("#")
        r = int(int(hex_color[0:2], 16) * factor)
        g = int(int(hex_color[2:4], 16) * factor)
        b = int(int(hex_color[4:6], 16) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _mode_btns_enable(self, enable):
        """启用/禁用模式切换按钮"""
        state = "normal" if enable else "disabled"
        for btn in [self.btn_work, self.btn_short, self.btn_long]:
            if enable:
                btn.configure(cursor="hand2")
            else:
                btn.configure(cursor="")

    def _update_tomato_icons(self):
        """更新番茄图标"""
        icons = "🍅 " * (self.session_count % LONG_BREAK_INTERVAL)
        self.tomato_icons.configure(text=icons)

    def _toggle_topmost(self, event=None):
        """切换窗口置顶"""
        current = self.topmost.get()
        self.topmost.set(not current)
        self.root.wm_attributes("-topmost", not current)
        self.pin_btn.configure(
            fg=COLOR_TOMATO if not current else COLOR_TEXT_SECONDARY
        )

    def _on_close(self):
        """关闭窗口"""
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.root.destroy()

    # ══════════════════════════════════════════════════════
    #  入口
    # ══════════════════════════════════════════════════════

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
