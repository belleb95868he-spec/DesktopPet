from PySide6.QtCore import QPoint, QRect, QTimer, Qt
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication, QLabel, QWidget


class SpeechBubble(QWidget):
    """独立显示、尺寸自适应的圆角气泡。"""

    def __init__(self):
        super().__init__(None)

        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        # Ensure the system does not draw a default background for this window
        # so the rounded bubble drawn in paintEvent is the only visible content.
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        self.text_label = QLabel(self)

        self.text_label.setAlignment(
            Qt.AlignCenter
        )

        self.text_label.setWordWrap(True)

        self.text_label.setStyleSheet(
            """
            QLabel {
                color: #444444;
                font-size: 13px;
                background: transparent;
                border: none;
                padding: 0px;
            }
            """
        )

        # =========================
        # 气泡尺寸参数
        # =========================

        # 文字区域的最小宽度
        self.min_text_width = 45

        # 文字区域的最大宽度
        # 超过这个宽度后自动换行
        self.max_text_width = 170

        # 左右留白
        self.padding_x = 15

        # 上下留白
        self.padding_y = 7

        # 气泡尾巴高度
        self.tail_height = 8

        # 圆角大小
        self.radius = 14

        # 尾巴宽度的一半
        self.tail_half_width = 8.0

        # 尾巴位置
        # 0.5 为气泡正中间
        self.tail_position = 0.43

        self.hide()

    def set_text(self, text):
        """根据文字长度自动调整气泡宽度和高度。"""

        text = str(text).strip()

        if not text:
            return

        self.text_label.setText(text)

        # 获取当前字体的尺寸信息
        font_metrics = QFontMetrics(
            self.text_label.font()
        )

        # 计算每一行文字的自然宽度
        text_lines = text.splitlines()

        natural_width = max(
            font_metrics.horizontalAdvance(line)
            for line in text_lines
        )

        # 在最小宽度与最大宽度之间自动调整
        content_width = max(
            self.min_text_width,
            min(
                natural_width,
                self.max_text_width
            )
        )

        # 为文字留出少量空间，
        # 避免最后一个字靠得太紧
        content_width += 4

        # 计算自动换行后的文字高度
        text_rect = font_metrics.boundingRect(
            QRect(
                0,
                0,
                content_width,
                1000
            ),
            int(
                Qt.TextWordWrap
                | Qt.AlignCenter
            ),
            text
        )

        content_height = max(
            font_metrics.lineSpacing(),
            text_rect.height()
        )

        # 设置文字 QLabel 的尺寸
        self.text_label.setFixedSize(
            content_width,
            content_height
        )

        # 计算整个气泡的宽度
        bubble_width = (
            content_width
            + self.padding_x * 2
        )

        # 计算气泡主体高度
        bubble_body_height = (
            content_height
            + self.padding_y * 2
        )

        # 设置整个气泡尺寸
        self.resize(
            bubble_width,
            bubble_body_height
            + self.tail_height
        )

        # 设置文字在气泡中的位置
        self.text_label.setGeometry(
            self.padding_x,
            self.padding_y,
            content_width,
            content_height
        )

        self.update()

    def paintEvent(self, event):
        # Keep paintEvent as implemented below; this placeholder
        # ensures any external calls land here when we instrument.
        super().paintEvent(event)

    def paintEvent(self, event):
        """绘制气泡框和三角形尾巴。"""

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        pen = QPen(
            QColor(125, 125, 125, 110)
        )

        pen.setWidthF(1.0)

        painter.setPen(pen)

        painter.setBrush(
            QColor(255, 255, 255, 245)
        )

        width = float(self.width())

        body_bottom = float(
            self.height()
            - self.tail_height
        )

        radius = float(self.radius)

        tail_center = (
            width
            * self.tail_position
        )

        tail_tip_y = float(
            self.height() - 1
        )

        path = QPainterPath()

        path.moveTo(
            radius,
            1.0
        )

        # 上边
        path.lineTo(
            width - radius,
            1.0
        )

        # 右上圆角
        path.quadTo(
            width - 1.0,
            1.0,
            width - 1.0,
            radius
        )

        # 右边
        path.lineTo(
            width - 1.0,
            body_bottom - radius
        )

        # 右下圆角
        path.quadTo(
            width - 1.0,
            body_bottom - 1.0,
            width - radius,
            body_bottom - 1.0
        )

        # 尾巴右侧
        path.lineTo(
            tail_center
            + self.tail_half_width,
            body_bottom - 1.0
        )

        # 尾巴尖端
        path.lineTo(
            tail_center,
            tail_tip_y
        )

        # 尾巴左侧
        path.lineTo(
            tail_center
            - self.tail_half_width,
            body_bottom - 1.0
        )

        # 下边
        path.lineTo(
            radius,
            body_bottom - 1.0
        )

        # 左下圆角
        path.quadTo(
            1.0,
            body_bottom - 1.0,
            1.0,
            body_bottom - radius
        )

        # 左边
        path.lineTo(
            1.0,
            radius
        )

        # 左上圆角
        path.quadTo(
            1.0,
            1.0,
            radius,
            1.0
        )

        path.closeSubpath()

        painter.drawPath(path)


class DialogueManager:
    """统一管理桌宠说话气泡。"""

    def __init__(self, pet):
        self.pet = pet

        self.dialogue_label = SpeechBubble()

        # 气泡自动隐藏计时器
        self.hide_timer = QTimer(
            self.pet
        )

        self.hide_timer.setSingleShot(
            True
        )

        self.hide_timer.timeout.connect(
            self.hide_message
        )

        # 气泡跟随人物计时器
        self.follow_timer = QTimer(
            self.pet
        )

        self.follow_timer.setInterval(
            16
        )

        self.follow_timer.timeout.connect(
            self.update_position
        )

        # 气泡与人物顶部之间的距离
        # 数值越大，气泡越往上
        self.distance = 0

        # 人物图片顶部存在透明区域时使用
        # 数值越大，气泡越往下
        self.head_offset = 0

    def show_message(
        self,
        text,
        duration=5000,
        allow_during_work=False,
    ):
        """显示一条对话。"""

        if (
            self.pet.is_interaction_locked()
            and not allow_during_work
        ):
            return

        if not text:
            return

        # 设置文字并自动调整气泡尺寸
        self.dialogue_label.set_text(
            text
        )

        print(f"[DialogueManager] show_message called: {text}")

        self.dialogue_label.show()
        self.dialogue_label.raise_()
        self.dialogue_label.setWindowOpacity(1.0)
        self.dialogue_label.setFocus(Qt.OtherFocusReason)
        self.dialogue_label.activateWindow()
        self.dialogue_label.setVisible(True)

        # 再次延迟 raise 一次，帮助在其他应用为活动窗口时也能把气泡带到前台
        QTimer.singleShot(50, lambda: (self.dialogue_label.raise_(), QApplication.processEvents(), print(f"[DialogueManager] bubble visible: {self.dialogue_label.isVisible()}")))

        # 气泡宽度改变后重新计算位置
        self.update_position()
        QApplication.processEvents()

        # 人物移动时持续更新位置
        self.follow_timer.start()

        # 重新开始隐藏倒计时
        self.hide_timer.start(
            duration
        )

    def hide_message(self):
        """隐藏气泡。"""

        self.dialogue_label.hide()
        self.follow_timer.stop()

    def update_position(self):
        """让气泡持续跟随人物。"""

        bubble = self.dialogue_label

        if not bubble.isVisible():
            return

        # 获取人物在桌面上的全局坐标
        pet_global_pos = (
            self.pet.pet_label.mapToGlobal(
                QPoint(0, 0)
            )
        )

        # 气泡与人物水平居中
        x = (
            pet_global_pos.x()
            + (
                self.pet.pet_label.width()
                - bubble.width()
            ) // 2
        )

        # 气泡显示在人物上方
        y = (
            pet_global_pos.y()
            + self.head_offset
            - bubble.height()
            - self.distance
        )

        bubble.move(
            x,
            y
        )
