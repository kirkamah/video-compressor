"""Главное окно приложения «Видео-компрессор» (CustomTkinter + drag&drop)."""

from __future__ import annotations

import queue
import threading
import tkinter.messagebox as mbox
import webbrowser
from pathlib import Path

import customtkinter as ctk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _HAS_DND = True
except Exception:  # pragma: no cover - DnD необязателен
    _HAS_DND = False

from .. import context_menu, presets, sizing, trial
from ..encoder import CancelledError, Encoder, EncodeSettings, quick_sample_estimate_mb
from ..ffprobe import MediaInfo, probe
from ..naming import unique_output_path
from ..paths import asset_path, ensure_engines

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


def _fmt_size(mb: float) -> str:
    if mb >= 1024:
        return f"{mb / 1024:.2f} ГБ"
    return f"{mb:.1f} МБ"


def _fmt_duration(s: float) -> str:
    s = int(round(s))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


# Базовый класс окна: с поддержкой DnD, если библиотека доступна.
if _HAS_DND:
    class _Root(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self):
            super().__init__()
            self.TkdndVersion = TkinterDnD._require(self)
else:
    class _Root(ctk.CTk):
        pass


class App(_Root):
    def __init__(self, initial_file: str | None = None):
        super().__init__()
        if trial.TRIAL:
            self.title("Видео-компрессор — Пробная версия")
        else:
            self.title("Видео-компрессор")
        self.geometry("560x640")
        # Окно фиксированного размера: нельзя растянуть/сжать/тянуть за края.
        self.resizable(False, False)
        self._set_window_icon()

        self.info: MediaInfo | None = None
        self.encoder: Encoder | None = None
        self._q: queue.Queue = queue.Queue()
        self._busy = False

        self._build_ui()
        self.after(100, self._poll_queue)

        if initial_file:
            self._load_file(initial_file)

    def _set_window_icon(self) -> None:
        ico = asset_path("app.ico")
        if ico.exists():
            try:
                self.iconbitmap(default=str(ico))
            except Exception:
                pass

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 6}

        ctk.CTkLabel(
            self, text="Видео-компрессор",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(14, 2))
        ctk.CTkLabel(
            self, text="Уменьшайте размер видео для пересылки",
            text_color=("gray40", "gray70"),
        ).pack()
        if trial.TRIAL:
            badge = ctk.CTkLabel(
                self,
                text="Пробная версия (до 5 минут) — полная на Boosty",
                text_color=("#b8860b", "#ffcc66"),
                font=ctk.CTkFont(size=12, underline=True),
                cursor="hand2",
            )
            badge.pack()
            badge.bind("<Button-1>", lambda _e: webbrowser.open(trial.BOOSTY_URL))

        # Зона перетаскивания / выбора файла.
        self.drop = ctk.CTkFrame(self, height=90, fg_color=("gray85", "gray20"))
        self.drop.pack(fill="x", **pad)
        self.drop.pack_propagate(False)
        self.drop_label = ctk.CTkLabel(
            self.drop,
            text="Перетащите видео сюда\nили нажмите «Выбрать файл»",
            justify="center",
        )
        self.drop_label.pack(expand=True)
        if _HAS_DND:
            self.drop.drop_target_register(DND_FILES)
            self.drop.dnd_bind("<<Drop>>", self._on_drop)

        ctk.CTkButton(self, text="Выбрать файл", command=self._browse).pack(**pad)

        self.info_label = ctk.CTkLabel(self, text="Файл не выбран", justify="left")
        self.info_label.pack(**pad)

        # Переключатель режима.
        self.mode = ctk.CTkSegmentedButton(
            self, values=["По размеру", "По качеству"], command=self._on_mode_change,
        )
        self.mode.set("По размеру")
        self.mode.pack(**pad)

        # --- Кадр режима «по размеру» ---
        self.size_frame = ctk.CTkFrame(self)
        ctk.CTkLabel(self.size_frame, text="Целевой размер:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.preset_menu = ctk.CTkOptionMenu(
            self.size_frame,
            values=[p.label for p in presets.SIZE_PRESETS] + ["Свой размер…"],
            command=lambda _=None: self._update_estimate(),
        )
        self.preset_menu.set(presets.SIZE_PRESETS[1].label)  # Discord 25 МБ
        self.preset_menu.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        self.custom_entry = ctk.CTkEntry(self.size_frame, placeholder_text="МБ", width=80)
        self.custom_entry.grid(row=1, column=1, padx=10, pady=(0, 8), sticky="w")
        self.custom_entry.bind("<KeyRelease>", lambda _e: self._update_estimate())
        self.size_frame.grid_columnconfigure(1, weight=1)

        # --- Кадр режима «по качеству» ---
        self.quality_frame = ctk.CTkFrame(self)
        self.q_caption = ctk.CTkLabel(self.quality_frame, text="Качество: Среднее")
        self.q_caption.grid(row=0, column=0, columnspan=2, padx=10, pady=(8, 0), sticky="w")
        self.slider = ctk.CTkSlider(self.quality_frame, from_=0, to=100, command=self._on_slider)
        self.slider.set(55)
        self.slider.grid(row=1, column=0, columnspan=2, padx=10, pady=4, sticky="ew")
        ctk.CTkLabel(self.quality_frame, text="лучше", text_color=("gray40", "gray70")).grid(row=2, column=0, padx=10, sticky="w")
        ctk.CTkLabel(self.quality_frame, text="меньше", text_color=("gray40", "gray70")).grid(row=2, column=1, padx=10, sticky="e")
        self.refine_btn = ctk.CTkButton(
            self.quality_frame, text="Уточнить размер", width=140, command=self._refine_estimate,
        )
        self.refine_btn.grid(row=3, column=0, columnspan=2, pady=8)
        self.quality_frame.grid_columnconfigure((0, 1), weight=1)

        # Понижение разрешения.
        res_row = ctk.CTkFrame(self, fg_color="transparent")
        res_row.pack(fill="x", **pad)
        ctk.CTkLabel(res_row, text="Разрешение:").pack(side="left", padx=(0, 8))
        self.res_menu = ctk.CTkOptionMenu(
            res_row, values=list(presets.RESOLUTION_CAPS.keys()),
            command=lambda _=None: self._update_estimate(),
        )
        self.res_menu.set("Как в оригинале")
        self.res_menu.pack(side="left")

        # Оценка результата.
        self.estimate_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.estimate_label.pack(**pad)

        # Прогресс и кнопки.
        self.progress = ctk.CTkProgressBar(self)
        self.progress.set(0)
        self.progress.pack(fill="x", **pad)
        self.status = ctk.CTkLabel(self, text="", text_color=("gray40", "gray70"))
        self.status.pack()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", **pad)
        self.compress_btn = ctk.CTkButton(
            btn_row, text="Сжать", height=40,
            font=ctk.CTkFont(size=16, weight="bold"), command=self._start,
        )
        self.compress_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.cancel_btn = ctk.CTkButton(
            btn_row, text="Отмена", width=90, fg_color="gray", command=self._cancel,
            state="disabled",
        )
        self.cancel_btn.pack(side="left", padx=(4, 0))

        # Контекстное меню.
        menu_row = ctk.CTkFrame(self, fg_color="transparent")
        menu_row.pack(fill="x", padx=16, pady=(0, 10))
        self.menu_btn = ctk.CTkButton(menu_row, text="", command=self._toggle_menu, height=28)
        self.menu_btn.pack(fill="x")
        self._refresh_menu_btn()

        # Brand footer (no harm org).
        ctk.CTkLabel(
            self, text="no harm org - Kirkamah",
            font=ctk.CTkFont(size=11),
            text_color=("gray55", "gray55"),
        ).pack(side="bottom", pady=(0, 6))

        self._on_mode_change("По размеру")

    # -------------------------------------------------------------- helpers
    def _trial_blocked(self, duration_s: float) -> bool:
        """True, если в пробной версии файл длиннее лимита (и показан диалог)."""
        if not trial.TRIAL or duration_s <= trial.TRIAL_MAX_DURATION_S:
            return False
        if mbox.askyesno(
            "Пробная версия",
            trial.TRIAL_LIMIT_MESSAGE + "\n\nОткрыть страницу Boosty?",
        ):
            webbrowser.open(trial.BOOSTY_URL)
        return True

    def _refresh_menu_btn(self) -> None:
        try:
            installed = context_menu.is_installed()
        except Exception:
            installed = False
        self.menu_btn.configure(
            text="Убрать пункт «Сжать видео» из правого клика" if installed
            else "Добавить «Сжать видео» в меню правого клика"
        )

    def _toggle_menu(self) -> None:
        try:
            if context_menu.is_installed():
                context_menu.uninstall()
                mbox.showinfo("Готово", "Пункт удалён из контекстного меню.")
            else:
                context_menu.install()
                if mbox.askyesno(
                    "Готово",
                    "Пункт «Сжать видео» добавлен.\n\n"
                    "Чтобы он сразу появился в правом клике, нужно перезапустить "
                    "Проводник (все открытые окна папок закроются и откроются заново).\n\n"
                    "Перезапустить Проводник сейчас?",
                ):
                    context_menu.restart_explorer()
        except Exception as e:
            mbox.showerror("Ошибка", str(e))
        self._refresh_menu_btn()

    def _on_mode_change(self, value: str) -> None:
        if value == "По размеру":
            self.quality_frame.pack_forget()
            self.size_frame.pack(fill="x", padx=16, pady=6, after=self.mode)
        else:
            self.size_frame.pack_forget()
            self.quality_frame.pack(fill="x", padx=16, pady=6, after=self.mode)
        self._update_estimate()

    def _on_slider(self, _value=None) -> None:
        pct = self.slider.get()
        self.q_caption.configure(text=f"Качество: {presets.quality_label(pct)}")
        self._update_estimate()

    # ------------------------------------------------------------ загрузка
    def _browse(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Выберите видео",
            filetypes=[("Видеофайлы", " ".join(f"*{e}" for e in context_menu.EXTENSIONS)),
                       ("Все файлы", "*.*")],
        )
        if path:
            self._load_file(path)

    def _on_drop(self, event) -> None:
        data = event.data.strip()
        # tkinterdnd2 оборачивает пути с пробелами в фигурные скобки.
        if data.startswith("{"):
            data = data[1:].split("}")[0]
        else:
            data = data.split()[0]
        self._load_file(data)

    def _load_file(self, path: str) -> None:
        try:
            ensure_engines()
            self.info = probe(path)
        except Exception as e:
            mbox.showerror("Не удалось открыть файл", str(e))
            return
        i = self.info
        self.drop_label.configure(text=Path(path).name)
        self.info_label.configure(
            text=(
                f"Размер: {_fmt_size(i.size_bytes / (1024 * 1024))}   •   "
                f"Длительность: {_fmt_duration(i.duration_s)}\n"
                f"Разрешение: {i.width}×{i.height}   •   "
                f"Видео: {i.video_codec}, ~{i.video_kbps:.0f} кбит/с   •   "
                f"Звук: {i.audio_codec or 'нет'}"
            )
        )
        self.progress.set(0)
        self.status.configure(text="")
        self._update_estimate()
        if trial.TRIAL and i.duration_s > trial.TRIAL_MAX_DURATION_S:
            self.status.configure(text="Пробная версия: видео длиннее 5 минут")
            self._trial_blocked(i.duration_s)

    # ------------------------------------------------------------- оценка
    def _height_cap(self) -> int | None:
        return presets.RESOLUTION_CAPS[self.res_menu.get()]

    def _scale_factor(self) -> float:
        cap = self._height_cap()
        if not cap or not self.info or self.info.height <= 0:
            return 1.0
        if cap >= self.info.height:
            return 1.0
        return (cap / self.info.height) ** 2

    def _target_mb(self) -> float | None:
        if self.preset_menu.get() == "Свой размер…":
            try:
                return float(self.custom_entry.get().replace(",", "."))
            except ValueError:
                return None
        label = self.preset_menu.get()
        for p in presets.SIZE_PRESETS:
            if p.label == label:
                return p.size_mb
        return None

    def _update_estimate(self) -> None:
        if not self.info:
            self.estimate_label.configure(text="")
            return
        i = self.info
        if self.mode.get() == "По размеру":
            mb = self._target_mb()
            if mb is None:
                self.estimate_label.configure(text="Введите размер в МБ", text_color="orange")
                return
            plan = sizing.target_plan(mb, i.duration_s, min(i.audio_kbps, 128))
            text = f"Результат: ~{_fmt_size(mb)} (видео {plan.video_kbps} кбит/с)"
            if plan.note:
                text += f"\n{plan.note}"
            self.estimate_label.configure(text=text, text_color=("gray10", "gray90"))
        else:
            crf = presets.slider_to_crf(self.slider.get())
            est = sizing.estimate_crf_size_mb(
                crf, i.video_kbps, i.duration_s,
                audio_kbps=min(i.audio_kbps, 128), scale_factor=self._scale_factor(),
            )
            self.estimate_label.configure(
                text=f"Примерно: ~{_fmt_size(est)}  (CRF {crf})",
                text_color=("gray10", "gray90"),
            )

    def _refine_estimate(self) -> None:
        if not self.info or self._busy:
            return
        self.refine_btn.configure(state="disabled", text="Считаю…")
        crf = presets.slider_to_crf(self.slider.get())
        cap = self._height_cap()
        info = self.info

        def work():
            try:
                est = quick_sample_estimate_mb(
                    info.path, crf, info.duration_s,
                    min(info.audio_kbps, 128), height_cap=cap,
                )
                self._q.put(("refine_ok", est, crf))
            except Exception as e:
                self._q.put(("refine_err", str(e)))

        threading.Thread(target=work, daemon=True).start()

    # ----------------------------------------------------------- кодирование
    def _start(self) -> None:
        if self._busy:
            return
        if not self.info:
            mbox.showwarning("Нет файла", "Сначала выберите видеофайл.")
            return
        i = self.info
        if self._trial_blocked(i.duration_s):
            return
        dst = unique_output_path(i.path)
        cap = self._height_cap()

        if self.mode.get() == "По размеру":
            mb = self._target_mb()
            if mb is None or mb <= 0:
                mbox.showwarning("Размер", "Укажите корректный целевой размер в МБ.")
                return
            plan = sizing.target_plan(mb, i.duration_s, min(i.audio_kbps, 128))
            if not plan.feasible and cap is None:
                if not mbox.askyesno(
                    "Маленький размер",
                    plan.note + "\n\nПродолжить без понижения разрешения?",
                ):
                    return
            settings = EncodeSettings(
                src=i.path, dst=dst, duration_s=i.duration_s, mode="size",
                video_kbps=plan.video_kbps, audio_kbps=plan.audio_kbps, height_cap=cap,
            )
        else:
            crf = presets.slider_to_crf(self.slider.get())
            settings = EncodeSettings(
                src=i.path, dst=dst, duration_s=i.duration_s, mode="quality",
                crf=crf, audio_kbps=min(i.audio_kbps, 128), height_cap=cap,
            )

        self.encoder = Encoder(settings)
        self._set_busy(True)
        self.status.configure(text="Сжатие…")
        self.progress.set(0)

        def work():
            try:
                out = self.encoder.run(on_progress=lambda f: self._q.put(("progress", f)))
                self._q.put(("done", out))
            except CancelledError:
                self._q.put(("cancelled",))
            except Exception as e:
                self._q.put(("error", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _cancel(self) -> None:
        if self.encoder:
            self.encoder.cancel()
            self.status.configure(text="Отмена…")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.compress_btn.configure(state="disabled" if busy else "normal")
        self.cancel_btn.configure(state="normal" if busy else "disabled")

    # ------------------------------------------------------- очередь событий
    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._q.get_nowait()
                self._handle(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _handle(self, msg: tuple) -> None:
        kind = msg[0]
        if kind == "progress":
            self.progress.set(msg[1])
            self.status.configure(text=f"Сжатие… {msg[1] * 100:.0f}%")
        elif kind == "done":
            out = Path(msg[1])
            self.progress.set(1.0)
            self._set_busy(False)
            new_mb = out.stat().st_size / (1024 * 1024)
            old_mb = self.info.size_bytes / (1024 * 1024) if self.info else 0
            saved = (1 - new_mb / old_mb) * 100 if old_mb else 0
            self.status.configure(text=f"Готово: {_fmt_size(new_mb)} (−{saved:.0f}%)")
            mbox.showinfo(
                "Готово",
                f"Файл сохранён:\n{out}\n\n"
                f"Было: {_fmt_size(old_mb)}\nСтало: {_fmt_size(new_mb)} (−{saved:.0f}%)",
            )
        elif kind == "cancelled":
            self._set_busy(False)
            self.progress.set(0)
            self.status.configure(text="Отменено")
        elif kind == "error":
            self._set_busy(False)
            self.progress.set(0)
            self.status.configure(text="Ошибка")
            mbox.showerror("Ошибка сжатия", msg[1])
        elif kind == "refine_ok":
            self.refine_btn.configure(state="normal", text="Уточнить размер")
            self.estimate_label.configure(
                text=f"Точнее: ~{_fmt_size(msg[1])}  (CRF {msg[2]})",
                text_color=("gray10", "gray90"),
            )
        elif kind == "refine_err":
            self.refine_btn.configure(state="normal", text="Уточнить размер")
            self.status.configure(text="Не удалось уточнить размер")


def run(initial_file: str | None = None) -> None:
    App(initial_file).mainloop()
