"""设置面板：左侧分页，所有改动实时生效。"""

from __future__ import annotations

import datetime
import os
import tempfile

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt5.QtGui import (
    QColor, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap,
)
from PyQt5.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSlider,
    QTabWidget, QToolButton, QVBoxLayout, QWidget,
)

from core import i18n, timezones
from core.config import THEME_ORDER, theme_name
from core.i18n import t
from core.logger import log_exception
from render import registry
from render.base import is_dark

THUMB = 104
LABEL_W = 120  # 英文标签比中文长，留够宽度免得被截断
CHECK_ICON = os.path.join(tempfile.gettempdir(), "desktopclock_check.png")


def _ensure_check_icon() -> str:
    """画一个白色对勾，供 QSS 的 checkbox 使用。"""
    try:
        if os.path.exists(CHECK_ICON):
            return CHECK_ICON
        pm = QPixmap(36, 36)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor("#FFFFFF"), 3.4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(7.0, 18.5)
        path.lineTo(14.5, 26.0)
        path.lineTo(29.0, 9.0)
        p.drawPath(path)
        p.end()
        pm.save(CHECK_ICON, "PNG")
    except Exception:
        log_exception("check_icon")
    return CHECK_ICON


def _build_qss() -> str:
    icon = _ensure_check_icon().replace("\\", "/")
    return """
QDialog { background: #F7F3EB; }
QTabWidget::pane {
    border: 1px solid #E7DFD2;
    border-radius: 10px;
    background: #FFFFFF;
    top: -1px;
}
QTabBar::tab {
    background: transparent; color: #7A7166;
    padding: 8px 22px; margin-right: 2px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    font-size: 12px;
}
QTabBar::tab:selected { background: #FFFFFF; color: #2C2C2A; }
QTabBar::tab:hover:!selected { color: #2C2C2A; }
QLabel { color: #3A342C; font-size: 12px; background: transparent; }
QGroupBox {
    border: 1px solid #EAE3D5;
    border-radius: 9px;
    margin-top: 14px;
    padding: 14px 14px 12px 14px;
    font-size: 12px;
    color: #6B6255;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
QComboBox, QPushButton {
    background: #FFFFFF; border: 1px solid #DDD5C6;
    border-radius: 6px; padding: 5px 10px;
    color: #2C2C2A; font-size: 12px; min-height: 16px;
}
QComboBox:hover, QPushButton:hover { border-color: #C08A4E; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #FFFFFF; border: 1px solid #DDD5C6;
    selection-background-color: #F3EDE2; selection-color: #2C2C2A;
    outline: none; padding: 4px;
}
QSlider::groove:horizontal { height: 4px; background: #EAE3D5; border-radius: 2px; }
QSlider::sub-page:horizontal { height: 4px; background: #DFC79E; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #C08A4E; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}
QCheckBox { color: #3A342C; font-size: 12px; spacing: 8px; background: transparent; }
QCheckBox::indicator {
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid #CFC6B6; background: #FFFFFF;
}
QCheckBox::indicator:hover { border-color: #C08A4E; }
QCheckBox::indicator:checked {
    background: #C08A4E; border-color: #C08A4E;
    image: url("%s");
}
QScrollArea { border: none; background: transparent; }
QListWidget {
    border: 1px solid #EAE3D5; border-radius: 7px;
    background: #FFFFFF; font-size: 12px; outline: none;
}
QListWidget::item { padding: 4px 6px; border-radius: 4px; }
QListWidget::item:selected { background: #F3EDE2; color: #2C2C2A; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: #DCD3C2; border-radius: 4px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: #C08A4E; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { height: 0px; }
""" % icon


class ColorButton(QPushButton):
    def __init__(self, color_hex: str, on_change):
        super().__init__()
        self._color = color_hex
        self._on_change = on_change
        self.setFixedSize(96, 26)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._pick)
        self._refresh()

    def _refresh(self) -> None:
        fg = "#FFFFFF" if is_dark(QColor(self._color)) else "#1A1A1A"
        self.setText(self._color.upper())
        self.setStyleSheet(
            "QPushButton{background:%s;color:%s;border:1px solid #C9C0B0;"
            "border-radius:6px;font-size:11px;font-family:Consolas;padding:2px;}"
            % (self._color, fg)
        )

    def _pick(self) -> None:
        chosen = QColorDialog.getColor(QColor(self._color), self, t("选择颜色", "Choose colour"))
        if chosen.isValid():
            self._color = chosen.name()
            self._refresh()
            self._on_change(self._color)

    def set_color(self, value: str) -> None:
        self._color = value
        self._refresh()


class SettingsDialog(QDialog):
    def __init__(self, cfg, window, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.window = window
        self._loading = True
        self._skin_buttons: dict[str, QToolButton] = {}
        self._bg_widgets: list = []
        self._radius_slider = None

        self.setWindowTitle(t("桌面时钟 · 设置", "Desktop Clock · Settings"))
        self.setMinimumSize(780, 660)
        self.setStyleSheet(_build_qss())
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(600)
        self._save_timer.timeout.connect(self._flush)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_skin_tab(), t("皮肤", "Skin"))
        self.tabs.addTab(self._build_appearance_tab(), t("外观", "Appearance"))
        self.tabs.addTab(self._build_content_tab(), t("内容", "Content"))
        self.tabs.addTab(self._build_behavior_tab(), t("行为", "Behaviour"))
        root.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        btn_reset = QPushButton(t("恢复默认", "Reset"))
        btn_reset.setFixedWidth(92)
        btn_reset.clicked.connect(self._reset)
        bottom.addWidget(btn_reset)
        bottom.addStretch(1)
        hint = QLabel(t("所有改动即时生效，无需重启", "Changes apply instantly, no restart needed"))
        hint.setStyleSheet("color:#9C9285;font-size:11px;")
        bottom.addWidget(hint)
        btn_close = QPushButton(t("完成", "Done"))
        btn_close.setDefault(True)
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

        self._loading = False
        self._sync_dependent()

    # ------------------------------------------------------------ 工具

    def _row(self, form: QFormLayout, text: str, widget: QWidget) -> None:
        """统一标签宽度，保证各分组左边界对齐。"""
        lbl = QLabel(text)
        lbl.setFixedWidth(LABEL_W)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.addRow(lbl, widget)

    def _slider_row(self, form, label, minimum, maximum, value, on_change):
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(int(value))
        value_label = QLabel(str(int(value)))
        value_label.setFixedWidth(40)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label.setStyleSheet("color:#8A8175;font-family:Consolas;font-size:11px;")
        lay.addWidget(slider, 1)
        lay.addWidget(value_label)

        def _changed(v):
            value_label.setText(str(int(v)))
            on_change(int(v))

        slider.valueChanged.connect(_changed)
        self._row(form, label, holder)
        return slider

    def _scale_row(self, form, label, value, on_change):
        """0.5–3.0 的倍数滑杆，0.1 一档，右侧带一个「1.0」复位按钮。"""
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(5, 30)
        slider.setSingleStep(1)
        slider.setPageStep(2)
        try:
            slider.setValue(int(round(float(value) * 10)))
        except Exception:
            slider.setValue(10)

        value_label = QLabel("%.1f×" % (slider.value() / 10.0))
        value_label.setFixedWidth(42)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label.setStyleSheet("color:#8A8175;font-family:Consolas;font-size:11px;")

        btn_one = QPushButton("1.0")
        btn_one.setFixedWidth(40)
        btn_one.setToolTip(t("恢复默认 1.0×", "Reset to 1.0×"))
        btn_one.setCursor(Qt.PointingHandCursor)
        btn_one.clicked.connect(lambda: slider.setValue(10))

        def _changed(v):
            value_label.setText("%.1f×" % (v / 10.0))
            on_change(v / 10.0)

        slider.valueChanged.connect(_changed)
        # 拖拽时只重绘时钟，松手后才重画 13 张缩略图，否则会卡
        slider.sliderReleased.connect(self.refresh_thumbs)

        lay.addWidget(slider, 1)
        lay.addWidget(value_label)
        lay.addWidget(btn_one)
        self._row(form, label, holder)
        return slider

    def _apply(self) -> None:
        if self._loading:
            return
        try:
            self.window.apply_config()
            self._save_timer.start()
            self._sync_dependent()
        except Exception:
            log_exception("settings apply")

    def _flush(self) -> None:
        try:
            self.cfg.save()
        except Exception:
            log_exception("settings flush")

    def _set(self, path: str, value) -> None:
        self.cfg.set(path, value)
        self._apply()

    def _on_color_changed(self, path: str, value: str) -> None:
        self.cfg.set(path, value)
        self.refresh_thumbs()
        self._apply()

    def _sync_dependent(self) -> None:
        skin = registry.get_skin(self.cfg.get("skin", "glass"))
        own_bg = skin.wants_own_bg
        circle = getattr(skin, "shape", "rect") == "circle"
        for w in self._bg_widgets:
            w.setEnabled(not own_bg)
        if own_bg:
            self.bg_hint.setText(t("当前皮肤自带底色，背景相关设置对它不生效", "This skin paints its own background; the options above do not apply"))
            self.bg_hint.setVisible(True)
        elif circle:
            self.bg_hint.setText(t("圆形表盘不支持毛玻璃（模糊会糊出方块），选它会自动按填充处理", "Round dials can't use blur (it would smear into a square), so it falls back to solid fill"))
            self.bg_hint.setVisible(True)
        else:
            self.bg_hint.setVisible(False)
        if self._radius_slider is not None:
            self._radius_slider.setEnabled(not circle)

    # ------------------------------------------------------------ 皮肤页

    def _build_skin_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        desc = QLabel(t("点一下即可切换，缩略图就是真实绘制结果。深色款（翻页 / 霓虹 / 终端）自带底色，不受背景设置影响。", "Click to switch. Thumbnails are real renders. Dark skins (Flip / Neon / Terminal) paint their own background."))
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#8A8175;font-size:11px;")
        lay.addWidget(desc)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setSpacing(12)

        current = self.cfg.get("skin", "glass")
        for index, skin in enumerate(registry.SKINS):
            btn = QToolButton()
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setIconSize(QRectF(0, 0, THUMB, THUMB).size().toSize())
            btn.setIcon(QIcon(self._render_thumb(skin)))
            btn.setText(skin.name)
            btn.setCheckable(True)
            btn.setChecked(skin.id == current)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(THUMB + 28, THUMB + 46)
            btn.setToolTip(skin.desc)
            btn.setStyleSheet(
                "QToolButton{border:1px solid #E7DFD2;border-radius:10px;background:#FFFFFF;"
                "padding:7px;color:#5C5346;font-size:11px;}"
                "QToolButton:hover{border-color:#C08A4E;}"
                "QToolButton:checked{border:2px solid #C08A4E;background:#FDF8F0;color:#2C2C2A;}"
            )
            btn.clicked.connect(lambda _=False, s=skin.id: self._pick_skin(s))
            self._skin_buttons[skin.id] = btn
            grid.addWidget(btn, index // 4, index % 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grid_widget)
        lay.addWidget(scroll, 1)
        return page

    def _render_thumb(self, skin) -> QPixmap:
        pm = QPixmap(THUMB, THUMB)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setRenderHint(QPainter.TextAntialiasing, True)
            rect = QRectF(1, 1, THUMB - 2, THUMB - 2)
            circle = getattr(skin, "shape", "rect") == "circle"
            radius = rect.width() / 2.0 if circle else 9.0
            if not skin.wants_own_bg:
                p.setPen(QPen(QColor(self.cfg.get("appearance.border_color", "#E7DFD2")), 1))
                p.setBrush(QColor(self.cfg.get("appearance.bg_color", "#FAF6EE")))
                p.drawRoundedRect(rect, radius, radius)
            if circle:
                p.setClipRect(rect)
            else:
                path = QPainterPath()
                path.addRoundedRect(rect, radius, radius)
                p.setClipPath(path)
            skin.draw(p, rect, datetime.datetime.now(), self.cfg)
        except Exception:
            log_exception("render_thumb")
        finally:
            p.end()
        return pm

    def _pick_skin(self, skin_id: str) -> None:
        try:
            self.cfg.set("skin", skin_id)
            for sid, btn in self._skin_buttons.items():
                btn.setChecked(sid == skin_id)
            self._apply()
        except Exception:
            log_exception("pick_skin")

    def refresh_thumbs(self) -> None:
        for skin in registry.SKINS:
            btn = self._skin_buttons.get(skin.id)
            if btn is not None:
                btn.setIcon(QIcon(self._render_thumb(skin)))

    # ------------------------------------------------------------ 外观页

    def _build_appearance_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(18, 18, 18, 14)
        lay.setSpacing(12)

        box_size = QGroupBox(t("尺寸与形状", "Size and shape"))
        f1 = QFormLayout(box_size)
        f1.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f1.setHorizontalSpacing(12)
        self._slider_row(f1, t("时钟大小", "Clock size"), 80, 600, self.cfg.get("geometry.size", 220),
                         lambda v: self._set("geometry.size", v))
        self._radius_slider = self._slider_row(f1, t("圆角", "Corner radius"), 0, 40,
                                               self.cfg.get("appearance.radius", 18),
                                               lambda v: self._set("appearance.radius", v))
        lay.addWidget(box_size)

        box_color = QGroupBox(t("配色", "Colours"))
        f2 = QFormLayout(box_color)
        f2.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f2.setHorizontalSpacing(12)

        self.theme_combo = QComboBox()
        for key in THEME_ORDER:
            self.theme_combo.addItem(theme_name(key), key)
        idx = self.theme_combo.findData(self.cfg.get("theme", "warm"))
        self.theme_combo.setCurrentIndex(max(0, idx))
        self.theme_combo.currentIndexChanged.connect(self._on_theme)
        self._row(f2, t("主题预设", "Theme preset"), self.theme_combo)

        self.btn_bg = ColorButton(self.cfg.get("appearance.bg_color", "#FAF6EE"),
                                  lambda v: self._on_color_changed("appearance.bg_color", v))
        self._row(f2, t("背景色", "Background"), self.btn_bg)
        self.btn_text = ColorButton(self.cfg.get("appearance.text_color", "#2C2C2A"),
                                    lambda v: self._on_color_changed("appearance.text_color", v))
        self._row(f2, t("文字色", "Text"), self.btn_text)
        self.btn_accent = ColorButton(self.cfg.get("appearance.accent", "#C08A4E"),
                                      lambda v: self._on_color_changed("appearance.accent", v))
        self._row(f2, t("强调色", "Accent"), self.btn_accent)
        self.btn_border = ColorButton(self.cfg.get("appearance.border_color", "#E7DFD2"),
                                      lambda v: self._on_color_changed("appearance.border_color", v))
        self._row(f2, t("描边色", "Border"), self.btn_border)
        lay.addWidget(box_color)

        box_bg = QGroupBox(t("背景与投影", "Background and shadow"))
        f3 = QFormLayout(box_bg)
        f3.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f3.setHorizontalSpacing(12)

        self.bg_mode_combo = QComboBox()
        self.bg_mode_combo.addItem(t("无底（纯悬浮）", "None (floating)"), "none")
        self.bg_mode_combo.addItem(t("填充", "Solid fill"), "solid")
        self.bg_mode_combo.addItem(t("毛玻璃（系统模糊）", "Frosted glass (system blur)"), "blur")
        i = self.bg_mode_combo.findData(self.cfg.get("appearance.bg_mode", "solid"))
        self.bg_mode_combo.setCurrentIndex(max(0, i))
        self.bg_mode_combo.currentIndexChanged.connect(
            lambda: self._set("appearance.bg_mode", self.bg_mode_combo.currentData()))
        self._row(f3, t("背景模式", "Background mode"), self.bg_mode_combo)

        self.opacity_slider = self._slider_row(f3, t("背景不透明度", "Opacity"), 0, 100,
                                               self.cfg.get("appearance.bg_opacity", 92),
                                               lambda v: self._set("appearance.bg_opacity", v))

        self.chk_border = QCheckBox(t("显示描边", "Show border"))
        self.chk_border.setChecked(self.cfg.get("appearance.border", True))
        self.chk_border.toggled.connect(lambda c: self._set("appearance.border", c))
        self._row(f3, "", self.chk_border)

        self.chk_shadow = QCheckBox(t("显示投影", "Show shadow"))
        self.chk_shadow.setChecked(self.cfg.get("appearance.shadow", True))
        self.chk_shadow.toggled.connect(lambda c: self._set("appearance.shadow", c))
        self._row(f3, "", self.chk_shadow)

        self.shadow_slider = self._slider_row(f3, t("投影强度", "Shadow strength"), 0, 40,
                                              self.cfg.get("appearance.shadow_strength", 20),
                                              lambda v: self._set("appearance.shadow_strength", v))

        self.bg_hint = QLabel(t("当前皮肤自带底色，背景相关设置对它不生效", "This skin paints its own background; the options above do not apply"))
        self.bg_hint.setStyleSheet("color:#B0894F;font-size:11px;")
        self.bg_hint.setVisible(False)
        self._row(f3, "", self.bg_hint)
        lay.addWidget(box_bg)

        self._bg_widgets = [self.bg_mode_combo, self.opacity_slider, self.btn_bg,
                            self.chk_border, self.btn_border]

        box_font = QGroupBox(t("字体与表盘", "Font and dial"))
        f4 = QFormLayout(box_font)
        f4.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f4.setHorizontalSpacing(12)

        self.font_combo = QComboBox()
        self.font_combo.addItems(QFontDatabase().families())
        j = self.font_combo.findText(self.cfg.get("appearance.font_family", "Consolas"))
        if j >= 0:
            self.font_combo.setCurrentIndex(j)
        self.font_combo.currentTextChanged.connect(lambda t: self._set("appearance.font_family", t))
        self._row(f4, t("数字字体", "Digit font"), self.font_combo)

        self.weight_combo = QComboBox()
        for val, label in ((300, t("细", "Light")), (400, t("常规", "Regular")), (500, t("中等", "Medium")), (700, t("粗", "Bold")), (900, t("特粗", "Black"))):
            self.weight_combo.addItem(label, val)
        k = self.weight_combo.findData(int(self.cfg.get("appearance.font_weight", 500)))
        self.weight_combo.setCurrentIndex(max(0, k))
        self.weight_combo.currentIndexChanged.connect(
            lambda: self._set("appearance.font_weight", self.weight_combo.currentData()))
        self._row(f4, t("数字字重", "Font weight"), self.weight_combo)

        self.dial_combo = QComboBox()
        self.dial_combo.addItem(t("阿拉伯数字", "Arabic numerals"), "arabic")
        self.dial_combo.addItem(t("不显示数字", "No numerals"), "none")
        m = self.dial_combo.findData(self.cfg.get("appearance.dial_style", "arabic"))
        self.dial_combo.setCurrentIndex(max(0, m))
        self.dial_combo.currentIndexChanged.connect(
            lambda: self._set("appearance.dial_style", self.dial_combo.currentData()))
        self._row(f4, t("表盘数字", "Dial numerals"), self.dial_combo)
        lay.addWidget(box_font)

        box_stroke = QGroupBox(t("指针与刻度", "Hands and ticks"))
        f5 = QFormLayout(box_stroke)
        f5.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f5.setHorizontalSpacing(12)

        self.hand_slider = self._scale_row(
            f5, t("指针粗细", "Hand weight"), self.cfg.get("appearance.hand_scale", 1.0),
            lambda v: self._set("appearance.hand_scale", v))
        self.dial_slider = self._scale_row(
            f5, t("表盘刻度", "Dial ticks"), self.cfg.get("appearance.dial_scale", 1.0),
            lambda v: self._set("appearance.dial_scale", v))

        stroke_hint = QLabel(
            t("1.0 为默认，0.1 一档，范围 0.5–3.0。表盘刻度只影响指针类皮肤"
              "（经典指针 / 经典挂钟 / 航海罗盘 / 怀表 / 香槟放射 / 罗马指针 / "
              "极简刻度盘 / 圆点刻度 / 双表盘）的刻度与数字。",
              "Default 1.0, step 0.1, range 0.5–3.0. Dial ticks only affect round-dial skins "
              "(Classic, Wall, Compass, Pocket, Sunburst, Roman, Minimal, Dot, Sub-dial)."))
        stroke_hint.setWordWrap(True)
        stroke_hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        stroke_hint.setStyleSheet("color:#9C9285;font-size:11px;")
        f5.addRow("", stroke_hint)
        lay.addWidget(box_stroke)

        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return page

    def _on_theme(self) -> None:
        key = self.theme_combo.currentData()
        if not key:
            return
        self.cfg.apply_theme(key)
        self.btn_bg.set_color(self.cfg.get("appearance.bg_color"))
        self.btn_text.set_color(self.cfg.get("appearance.text_color"))
        self.btn_accent.set_color(self.cfg.get("appearance.accent"))
        self.btn_border.set_color(self.cfg.get("appearance.border_color"))
        self.refresh_thumbs()
        self._apply()

    # ------------------------------------------------------------ 内容页

    def _build_content_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(18, 18, 18, 14)
        lay.setSpacing(12)

        box_time = QGroupBox(t("时间显示", "Time"))
        f = QFormLayout(box_time)
        f.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f.setHorizontalSpacing(12)

        self.chk_h24 = QCheckBox(t("24 小时制", "24-hour clock"))
        self.chk_h24.setChecked(self.cfg.get("content.hour24", True))
        self.chk_h24.toggled.connect(lambda c: self._set("content.hour24", c))
        self._row(f, "", self.chk_h24)

        self.chk_sec = QCheckBox(t("显示秒", "Show seconds"))
        self.chk_sec.setChecked(self.cfg.get("content.show_seconds", True))
        self.chk_sec.toggled.connect(lambda c: self._set("content.show_seconds", c))
        self._row(f, "", self.chk_sec)

        self.sec_style = QComboBox()
        self.sec_style.addItem(t("跳秒（省电）", "Tick (low power)"), "tick")
        self.sec_style.addItem(t("平滑扫秒（30fps）", "Sweep (30 fps)"), "smooth")
        self.sec_style.addItem(t("不显示秒针", "No second hand"), "none")
        s = self.sec_style.findData(self.cfg.get("content.second_style", "tick"))
        self.sec_style.setCurrentIndex(max(0, s))
        self.sec_style.currentIndexChanged.connect(
            lambda: self._set("content.second_style", self.sec_style.currentData()))
        self._row(f, t("秒针样式", "Second hand"), self.sec_style)

        self.date_combo = QComboBox()
        for label, val in ((t("10月25日", "Oct 25"), "MM月DD日"), ("2026-10-25", "YYYY-MM-DD"),
                           ("10.25", "MM.DD"), ("2026/10/25", "YYYY/MM/DD"),
                           (t("不显示", "None"), "")):
            self.date_combo.addItem(label, val)
        d = self.date_combo.findData(self.cfg.get("content.date_format", "MM月DD日"))
        self.date_combo.setCurrentIndex(max(0, d))
        self.date_combo.currentIndexChanged.connect(
            lambda: self._set("content.date_format", self.date_combo.currentData()))
        self._row(f, t("日期格式", "Date format"), self.date_combo)

        self.wd_combo = QComboBox()
        for label, val in ((t("周日", "Mon"), "short"), (t("星期日", "Monday"), "full"), ("SUN", "en"), (t("不显示", "None"), "none")):
            self.wd_combo.addItem(label, val)
        w = self.wd_combo.findData(self.cfg.get("content.show_weekday", "short"))
        self.wd_combo.setCurrentIndex(max(0, w))
        self.wd_combo.currentIndexChanged.connect(
            lambda: self._set("content.show_weekday", self.wd_combo.currentData()))
        self._row(f, t("星期", "Weekday"), self.wd_combo)

        self.chk_lunar = QCheckBox(t("显示农历与节气", "Show lunar date & solar term"))
        self.chk_lunar.setChecked(self.cfg.get("content.show_lunar", False))
        self.chk_lunar.toggled.connect(lambda c: self._set("content.show_lunar", c))
        self._row(f, "", self.chk_lunar)

        self.chk_cursor = QCheckBox(t("终端皮肤显示闪烁光标", "Blinking cursor in the Terminal skin"))
        self.chk_cursor.setChecked(self.cfg.get("content.blink_cursor", True))
        self.chk_cursor.toggled.connect(lambda c: self._set("content.blink_cursor", c))
        self._row(f, "", self.chk_cursor)
        lay.addWidget(box_time)

        box_tz = QGroupBox(t("副时区城市（最多选 4 个，世界时钟皮肤使用）", "Extra time zones (up to 4, used by the World Clock skin)"))
        v = QVBoxLayout(box_tz)
        v.setContentsMargins(10, 6, 10, 10)
        self.tz_list = QListWidget()
        self.tz_list.setMaximumHeight(180)
        selected = set(self.cfg.get("content.sub_timezones") or [])
        for key, _cn, abbr, _tz, _off in timezones.CITIES:
            item = QListWidgetItem("%s   %s" % (timezones.city_label(key), abbr))
            item.setData(Qt.UserRole, key)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if key in selected else Qt.Unchecked)
            self.tz_list.addItem(item)
        self.tz_list.itemChanged.connect(self._on_tz_changed)
        v.addWidget(self.tz_list)
        lay.addWidget(box_tz)
        lay.addStretch(1)
        return page

    def _on_tz_changed(self, item) -> None:
        try:
            checked = []
            for i in range(self.tz_list.count()):
                it = self.tz_list.item(i)
                if it.checkState() == Qt.Checked:
                    checked.append(it.data(Qt.UserRole))
            if len(checked) > 4:
                self._loading = True
                item.setCheckState(Qt.Unchecked)
                self._loading = False
                return
            self._set("content.sub_timezones", checked)
        except Exception:
            log_exception("on_tz_changed")

    # ------------------------------------------------------------ 行为页

    def _build_behavior_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(18, 18, 18, 14)
        lay.setSpacing(12)

        box_general = QGroupBox(t("通用", "General"))
        fg = QFormLayout(box_general)
        fg.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fg.setHorizontalSpacing(12)

        self.lang_combo = QComboBox()
        for code, label in i18n.LANGUAGES:
            self.lang_combo.addItem(label, code)
        cur = self.lang_combo.findData(i18n.current())
        self.lang_combo.setCurrentIndex(max(0, cur))
        self.lang_combo.currentIndexChanged.connect(self._on_language)
        self._row(fg, t("界面语言", "Language"), self.lang_combo)

        lang_hint = QLabel(t("切换后设置面板会自动重开，托盘菜单同时生效。",
                             "The panel reopens itself after switching; the tray menu updates too."))
        lang_hint.setWordWrap(True)
        lang_hint.setStyleSheet("color:#9C9285;font-size:11px;")
        fg.addRow("", lang_hint)
        lay.addWidget(box_general)

        box_layer = QGroupBox(t("窗口层级", "Window layer"))
        f = QFormLayout(box_layer)
        f.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f.setHorizontalSpacing(12)

        self.layer_combo = QComboBox()
        self.layer_combo.addItem(t("始终置顶（压在普通窗口之上）", "Always on top (above normal windows)"), "topmost")
        self.layer_combo.addItem(t("普通窗口（可被遮挡）", "Normal window (can be covered)"), "normal")
        self.layer_combo.addItem(t("桌面挂件层（壁纸之上、图标之下）", "Desktop widget layer (above wallpaper, below icons)"), "desktop")
        li = self.layer_combo.findData(self.cfg.get("layer", "topmost"))
        self.layer_combo.setCurrentIndex(max(0, li))
        self.layer_combo.currentIndexChanged.connect(self._on_layer)
        self._row(f, t("层级", "Layer"), self.layer_combo)

        self.chk_guard = QCheckBox(t("置顶守护（防止被其它置顶窗口挤下）", "Topmost guard (stay above other topmost windows)"))
        self.chk_guard.setChecked(self.cfg.get("behavior.topmost_guard", True))
        self.chk_guard.toggled.connect(lambda c: self._set("behavior.topmost_guard", c))
        self._row(f, "", self.chk_guard)
        lay.addWidget(box_layer)

        box_inter = QGroupBox(t("交互", "Interaction"))
        f2 = QFormLayout(box_inter)
        f2.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f2.setHorizontalSpacing(12)

        self.chk_lock = QCheckBox(t("锁定位置（防止误拖）", "Lock position (no accidental drags)"))
        self.chk_lock.setChecked(self.cfg.get("behavior.lock_position", False))
        self.chk_lock.toggled.connect(lambda c: self._set("behavior.lock_position", c))
        self._row(f2, "", self.chk_lock)

        self.chk_through = QCheckBox(t("点击穿透（鼠标事件交给下方窗口）", "Click-through (pass clicks to the window below)"))
        self.chk_through.setChecked(self.cfg.get("behavior.click_through", False))
        self.chk_through.toggled.connect(lambda c: self._set("behavior.click_through", c))
        self._row(f2, "", self.chk_through)

        self.chk_snap = QCheckBox(t("靠近屏幕边缘时自动吸附", "Snap to screen edges"))
        self.chk_snap.setChecked(self.cfg.get("behavior.edge_snap", True))
        self.chk_snap.toggled.connect(lambda c: self._set("behavior.edge_snap", c))
        self._row(f2, "", self.chk_snap)
        lay.addWidget(box_inter)

        box_start = QGroupBox(t("启动", "Startup"))
        f3 = QFormLayout(box_start)
        f3.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f3.setHorizontalSpacing(12)
        self.chk_auto = QCheckBox(t("开机自动启动", "Start with Windows"))
        self.chk_auto.setChecked(self.cfg.get("behavior.autostart", False))
        self.chk_auto.toggled.connect(self._on_autostart)
        self._row(f3, "", self.chk_auto)
        lay.addWidget(box_start)

        box_key = QGroupBox(t("快捷键（全局生效）", "Hotkeys (global)"))
        f4 = QFormLayout(box_key)
        f4.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f4.setHorizontalSpacing(12)
        k1 = QLabel(self.cfg.get("behavior.hotkey_layer", "Ctrl+Alt+T"))
        k1.setStyleSheet("font-family:Consolas;color:#8A5B22;font-size:12px;")
        self._row(f4, t("循环切换层级", "Cycle window layer"), k1)
        k2 = QLabel(self.cfg.get("behavior.hotkey_visible", "Ctrl+Alt+H"))
        k2.setStyleSheet("font-family:Consolas;color:#8A5B22;font-size:12px;")
        self._row(f4, t("显示 / 隐藏", "Show / hide"), k2)
        lay.addWidget(box_key)

        tip = QLabel(t("桌面挂件层在部分系统上可能挂载失败，此时会自动降级为置顶并写入日志。", "The desktop widget layer can fail to attach on some systems; it then falls back to always-on-top and logs it."))
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#9C9285;font-size:11px;")
        lay.addWidget(tip)
        lay.addStretch(1)
        return page

    def _on_language(self) -> None:
        """切语言：存盘 + 立即生效，然后把自己关掉重开，让所有文字换成新语言。"""
        if self._loading:
            return
        code = self.lang_combo.currentData()
        if not code or code == i18n.current():
            return
        try:
            self.cfg.set("language", code)
            self.cfg.save()
            i18n.set_language(code)
            win = self.window
            self.accept()
            if win is not None:
                win.request_language.emit()
                QTimer.singleShot(0, win.request_settings.emit)
        except Exception:
            log_exception("on_language")

    def _on_layer(self) -> None:
        layer = self.layer_combo.currentData()
        if not layer:
            return
        self.cfg.set("layer", layer)
        self.window.apply_layer()
        self._apply()

    def _on_autostart(self, checked: bool) -> None:
        try:
            from sysint import autostart
            autostart.set_enabled(checked)
            self._set("behavior.autostart", checked)
        except Exception:
            log_exception("on_autostart")

    # ------------------------------------------------------------ 恢复默认

    def _reset(self) -> None:
        try:
            self.cfg.reset()
            self._loading = True
            self.chk_h24.setChecked(True)
            self.chk_sec.setChecked(True)
            self.chk_lunar.setChecked(False)
            self.chk_border.setChecked(True)
            self.chk_shadow.setChecked(True)
            self.btn_bg.set_color(self.cfg.get("appearance.bg_color"))
            self.btn_text.set_color(self.cfg.get("appearance.text_color"))
            self.btn_accent.set_color(self.cfg.get("appearance.accent"))
            self.btn_border.set_color(self.cfg.get("appearance.border_color"))
            self.hand_slider.setValue(10)
            self.dial_slider.setValue(10)
            ti = self.theme_combo.findData("warm")
            self.theme_combo.setCurrentIndex(max(0, ti))
            for sid, btn in self._skin_buttons.items():
                btn.setChecked(sid == "glass")
            self._loading = False
            self.refresh_thumbs()
            self.window.apply_config()
            self.cfg.save()
        except Exception:
            log_exception("reset")
