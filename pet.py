import math
import sys
from pathlib import Path

from PySide6.QtCore import (
    QElapsedTimer,
    QEasingCurve,
    QPoint,
    QEvent,
    QMimeData,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontDatabase,
    QDrag,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from animation_manager import AnimationManager
from dialogue import DialogueManager
from hourly_greetings import HourlyGreetingManager
from petting_manager import PettingManager
from status_manager import APPLE_PRICE, SHOP_PRICES, StatusManager


PROFILE_FONT = "乐米元气团团体"
SHOP_ITEMS = [
    ("ice", "棒冰", 3, "ice.png"),
    ("sausage", "烤肠", 6, "sausage.png"),
    ("apple", "苹果", 10, "apple.png"),
    ("milk", "牛奶", 12, "milk.png"),
    ("bread", "鸡腿面包", 20, "bread.png"),
    ("milktea", "奶茶", 25, "milktea.png"),
    ("drink", "能量饮料", 30, "drink.png"),
    ("ramen", "清汤拉面", 40, "ramen.png"),
    ("salad", "健康轻食", 45, "salad.png"),
]
SHOP_ITEM_MAP = {
    item[0]: item
    for item in SHOP_ITEMS
}
SHOP_HUNGER_VALUES = {
    "ice": 3,
    "sausage": 6,
    "apple": 10,
    "milk": 12,
    "bread": 20,
    "milktea": 15,
    "drink": 8,
    "ramen": 30,
    "salad": 25,
}
SHOP_DRAG_MIME = "application/x-desktop-pet-shop-item"


def load_hidpi_pixmap(path, width, height):
    """Scale an asset at screen pixel density while preserving its ratio."""
    pixmap = QPixmap(str(path))
    screen = QGuiApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen is not None else 1.0
    scaled = pixmap.scaled(
        round(width * ratio),
        round(height * ratio),
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(ratio)
    return scaled


def load_hidpi_icon(path, height=23, max_width=36):
    """Normalize status icons by visual height without changing aspect ratio."""
    pixmap = QPixmap(str(path))
    screen = QGuiApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen is not None else 1.0
    scaled = pixmap.scaledToHeight(
        round(height * ratio),
        Qt.SmoothTransformation,
    )
    if scaled.width() > round(max_width * ratio):
        scaled = pixmap.scaledToWidth(
            round(max_width * ratio),
            Qt.SmoothTransformation,
        )
    scaled.setDevicePixelRatio(ratio)
    return scaled


class ProfileProgressBar(QProgressBar):
    """Reference-style rounded progress bar drawn without bitmap UI."""

    def __init__(self, maximum=100, parent=None):
        super().__init__(parent)
        self.setRange(0, maximum)
        self.setTextVisible(False)
        self.setFixedSize(109, 15)
        self.setProperty("profileBar", True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = QRectF(self.rect())
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ddd2c2"))
        painter.drawRoundedRect(bounds, 7.5, 7.5)

        ratio = 0 if self.maximum() <= 0 else self.value() / self.maximum()
        fill_width = max(0.0, bounds.width() * ratio)
        if fill_width:
            painter.setBrush(QColor("#93dc38"))
            track_clip = QPainterPath()
            track_clip.addRoundedRect(bounds, 7.5, 7.5)
            painter.save()
            painter.setClipPath(track_clip)
            painter.drawRect(QRectF(0, 0, fill_width, bounds.height()))
            painter.restore()

        painter.setPen(QColor(85, 135, 47))
        font = QFont("Noto Sans")
        font.setPixelSize(9)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        if self.maximum() == 2000:
            text = f"{self.value()} / {self.maximum()}"
        else:
            text = f"{self.value()}% / {self.maximum()}%"
        painter.drawText(bounds, Qt.AlignCenter, text)


class ProfilePage(QWidget):
    """Native-size profile card using the provided frame as its background."""

    WIDTH = 382
    HEIGHT = 290
    SCALE_X = WIDTH / 601
    SCALE_Y = HEIGHT / 458

    def __init__(self, asset_root, parent=None):
        super().__init__(parent)
        self.asset_root = Path(asset_root)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(self.SCALE_X, self.SCALE_Y)

        frame = QPixmap(str(self.asset_root / "frame" / "Card Design.png"))
        painter.drawPixmap(
            QRectF(0, 0, 601, 458),
            frame,
            QRectF(frame.rect()),
        )
        painter.translate(-9, 0)

        # Portrait frame and ribbon remain code-drawn.
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#eadfce"), 3))
        painter.drawRect(QRectF(57, 162, 168, 200))

        # Ribbon and its folded ends.
        painter.setPen(Qt.NoPen)
        ribbon_gradient = QLinearGradient(0, 359, 0, 397)
        ribbon_gradient.setColorAt(0.0, QColor("#b8734b"))
        ribbon_gradient.setColorAt(0.48, QColor("#b8734b"))
        ribbon_gradient.setColorAt(0.52, QColor("#965633"))
        ribbon_gradient.setColorAt(1.0, QColor("#965633"))
        painter.setBrush(ribbon_gradient)
        ribbon = QPainterPath()
        ribbon.moveTo(57, 359)
        ribbon.lineTo(225, 359)
        ribbon.lineTo(215, 378)
        ribbon.lineTo(225, 397)
        ribbon.lineTo(57, 397)
        ribbon.lineTo(67, 378)
        ribbon.closeSubpath()
        painter.drawPath(ribbon)

        painter.setPen(QColor("#ffffff"))
        font = QFont(PROFILE_FONT)
        font.setPixelSize(round(15 / self.SCALE_Y))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(57, 360, 168, 37), Qt.AlignCenter, "Lv.20  L Xu")


class ShopItemCard(QWidget):
    selected = Signal(str)

    def __init__(self, item, asset_root, parent=None):
        super().__init__(parent)
        self.item_id, self.item_name, self.price, filename = item
        self.pixmap = QPixmap(str(asset_root / "ShopItem" / filename))
        self.is_selected = False
        self.is_hovered = False
        self.setFixedSize(56, 59)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.selected.emit(self.item_id)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        border = QColor("#f2c85c") if self.is_selected else QColor("#ffffff")
        if self.is_hovered and not self.is_selected:
            border = QColor("#f6dc9b")
        painter.setPen(QPen(border, 2))
        painter.setBrush(QColor("#fffaf0"))
        painter.drawRoundedRect(QRectF(7, 5, 48, 53), 5, 5)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#f1e2bd"))
        painter.drawRoundedRect(QRectF(12, 12, 38, 31), 5, 5)

        if self.item_id == "apple":
            image_rect = QRectF(19.1, 16.025, 23.8, 22.95)
        else:
            image_rect = QRectF(17, 14, 28, 27)
        painter.drawPixmap(image_rect, self.pixmap, QRectF(self.pixmap.rect()))

        painter.save()
        painter.translate(15, 7)
        painter.rotate(-15)
        painter.translate(-13.95, -7.2)
        ribbon = QPainterPath()
        ribbon.moveTo(0, 3.6)
        ribbon.lineTo(26.1, 0)
        ribbon.lineTo(27.9, 10.8)
        ribbon.lineTo(1.8, 14.4)
        ribbon.closeSubpath()
        painter.setBrush(QColor("#ca5900"))
        painter.drawPath(ribbon)
        font = QFont(PROFILE_FONT)
        font.setPixelSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(Qt.white)
        painter.drawText(QRectF(1, 0.9, 26.1, 12.6), Qt.AlignCenter, f"¥{self.price}")
        painter.restore()

        font.setPixelSize(10)
        font.setLetterSpacing(QFont.PercentageSpacing, 86)
        painter.setFont(font)
        painter.setPen(QColor("#775739"))
        painter.drawText(QRectF(7, 44, 48, 15), Qt.AlignCenter, self.item_name)


class ShopBackButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(58, 54)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pressed = self.isDown()

        # Solid ochre shadow, yellow rim, and warm-white button face.
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#9f7100"))
        painter.drawEllipse(QRectF(7, 2, 48, 48))
        painter.setBrush(QColor("#9f7100"))
        painter.drawEllipse(QRectF(7, 1, 48, 48))
        painter.setBrush(QColor("#f3bf19"))
        painter.drawEllipse(QRectF(9, 3, 44, 44))
        painter.setBrush(QColor("#fff8dd") if not pressed else QColor("#f5e8ba"))
        painter.drawEllipse(QRectF(12.5, 6.5, 37, 37))

        # Rounded arrow, centered on the circular button face.
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#d99400"))
        arrow = QPainterPath()
        arrow.moveTo(17, 25)
        arrow.quadTo(17, 24, 18, 23)
        arrow.lineTo(28, 14)
        arrow.quadTo(30, 12, 31, 14)
        arrow.lineTo(31, 19)
        arrow.lineTo(40, 19)
        arrow.quadTo(42, 19, 42, 21)
        arrow.lineTo(42, 29)
        arrow.quadTo(42, 31, 40, 31)
        arrow.lineTo(31, 31)
        arrow.lineTo(31, 36)
        arrow.quadTo(30, 38, 28, 36)
        arrow.lineTo(18, 27)
        arrow.quadTo(17, 26, 17, 25)
        arrow.closeSubpath()
        painter.translate(1.5, 0)
        painter.drawPath(arrow)


class ShopPurchaseButton(QPushButton):
    def __init__(self, coin_path, parent=None):
        super().__init__(parent)
        self.price = 10
        self.coin_pixmap = QPixmap(str(coin_path))
        self.setFixedSize(151, 35)
        self.setCursor(Qt.PointingHandCursor)

    def set_price(self, price):
        self.price = int(price)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if not self.isEnabled():
            fill, border = QColor("#b8c98e"), QColor("#8fa461")
        elif self.isDown():
            fill, border = QColor("#73bd26"), QColor("#5c9d1b")
        elif self.underMouse():
            fill, border = QColor("#9be23b"), QColor("#79bd27")
        else:
            fill, border = QColor("#88d62f"), QColor("#68b11d")
        painter.setPen(QPen(border, 2))
        painter.setBrush(fill)
        painter.drawRoundedRect(QRectF(1, 1, 149, 33), 16, 16)
        painter.drawPixmap(
            QRectF(24, 8, 19, 19),
            self.coin_pixmap,
            QRectF(self.coin_pixmap.rect()),
        )
        font = QFont(PROFILE_FONT)
        font.setPixelSize(16)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(Qt.white)
        painter.drawText(
            QRectF(43, 2, 92, 31),
            Qt.AlignCenter,
            f"¥ {self.price}  购买",
        )


class ShopPage(QWidget):
    itemSelected = Signal(str)
    purchaseRequested = Signal()
    backRequested = Signal()
    WIDTH = 430
    HEIGHT = 290

    def __init__(self, asset_root, parent=None):
        super().__init__(parent)
        self.asset_root = Path(asset_root)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.selected_item_id = "apple"
        self.coin_count = 0
        self.total_items = 0
        self.item_cards = {}
        self.preview_drag_start = QPoint()
        self.preview_drag_armed = False
        self.background = QPixmap(
            str(self.asset_root / "ShopBackground.png")
        )

        self.back_button = ShopBackButton(self)
        self.back_button.move(-17, 27)
        self.back_button.clicked.connect(self.backRequested)

        for index, item in enumerate(SHOP_ITEMS):
            card = ShopItemCard(item, self.asset_root, self)
            row_y = (60, 133, 204)[index // 3]
            card.move(212 + (index % 3) * 64, row_y)
            card.selected.connect(self.itemSelected)
            self.item_cards[item[0]] = card

        self.purchase_button = ShopPurchaseButton(
            self.asset_root / "ShopButton" / "coin.png",
            self,
        )
        self.purchase_button.move(33, 223)
        self.purchase_button.clicked.connect(self.purchaseRequested)
        self.select_item("apple")

    def select_item(self, item_id):
        if item_id not in SHOP_ITEM_MAP:
            return
        self.selected_item_id = item_id
        for card_id, card in self.item_cards.items():
            card.is_selected = card_id == item_id
            card.update()
        self.purchase_button.set_price(SHOP_ITEM_MAP[item_id][2])
        self.update()

    def set_economy(self, coin_count, total_items, can_buy):
        self.coin_count = max(0, int(coin_count))
        self.total_items = max(0, int(total_items))
        self.purchase_button.setEnabled(bool(can_buy))
        self.update()

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.LeftButton
            and QRectF(55, 72, 107, 107).contains(event.position())
        ):
            self.preview_drag_start = event.position().toPoint()
            self.preview_drag_armed = True
            event.accept()
            return
        self.preview_drag_armed = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            not self.preview_drag_armed
            or not (event.buttons() & Qt.LeftButton)
        ):
            super().mouseMoveEvent(event)
            return
        if (
            event.position().toPoint() - self.preview_drag_start
        ).manhattanLength() < QApplication.startDragDistance():
            event.accept()
            return

        item = SHOP_ITEM_MAP[self.selected_item_id]
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(
            SHOP_DRAG_MIME,
            self.selected_item_id.encode("utf-8"),
        )
        drag.setMimeData(mime_data)
        drag_pixmap = load_hidpi_pixmap(
            self.asset_root / "ShopItem" / item[3],
            48,
            48,
        )
        drag.setPixmap(drag_pixmap)
        drag.setHotSpot(QPoint(24, 24))
        drag.exec(Qt.CopyAction)
        self.preview_drag_start = QPoint()
        self.preview_drag_armed = False
        event.accept()

    def mouseReleaseEvent(self, event):
        self.preview_drag_armed = False
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        background_height = (
            self.width()
            * self.background.height()
            / self.background.width()
        )
        background_y = self.height() - background_height
        painter.drawPixmap(
            QRectF(0, background_y, self.width(), background_height),
            self.background,
            QRectF(self.background.rect()),
        )

        # Selected item preview.
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#d39c61"), 2))
        painter.drawRoundedRect(QRectF(55, 72, 107, 107), 10, 10)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#f5ead2"))
        painter.drawRoundedRect(QRectF(62, 80, 93, 83), 10, 10)
        painter.setBrush(QColor("#f7d278"))
        name_strip = QPainterPath()
        name_strip.moveTo(62, 150)
        name_strip.lineTo(155, 150)
        name_strip.lineTo(155, 163)
        name_strip.quadTo(155, 173, 145, 173)
        name_strip.lineTo(72, 173)
        name_strip.quadTo(62, 173, 62, 163)
        name_strip.closeSubpath()
        painter.drawPath(name_strip)

        item = SHOP_ITEM_MAP[self.selected_item_id]
        pixmap = QPixmap(str(self.asset_root / "ShopItem" / item[3]))
        if self.selected_item_id == "apple":
            preview_rect = QRectF(83.425, 90.35, 50.15, 49.3)
        else:
            preview_rect = QRectF(79, 86, 59, 58)
        painter.drawPixmap(preview_rect, pixmap, QRectF(pixmap.rect()))
        font = QFont(PROFILE_FONT)
        font.setBold(True)
        font.setPixelSize(15)
        painter.setFont(font)
        painter.setPen(QColor("#765637"))
        painter.drawText(QRectF(63, 150, 91, 23), Qt.AlignCenter, item[1])

        money_icon = QPixmap(str(self.asset_root / "StatusIcon" / "MoneyBag.png"))
        bag_icon = QPixmap(str(self.asset_root / "StatusIcon" / "Bag.png"))
        money_icon = money_icon.copy(10, 14, 59, 70)
        bag_icon = bag_icon.copy(19, 14, 59, 66)
        painter.setBrush(QColor("#a47a49"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(40, 187, 75, 25), 6, 6)
        painter.drawRoundedRect(QRectF(119, 187, 58, 25), 6, 6)
        painter.drawPixmap(
            QRectF(46.7, 191.85, 12.6, 15.3),
            money_icon,
            QRectF(money_icon.rect()),
        )
        painter.drawPixmap(
            QRectF(123.75, 191.85, 13.5, 15.3),
            bag_icon,
            QRectF(bag_icon.rect()),
        )
        font.setPixelSize(14)
        painter.setFont(font)
        painter.setPen(Qt.white)
        painter.drawText(QRectF(61, 188, 51, 22), Qt.AlignCenter, f"¥ {self.coin_count}")
        painter.drawText(QRectF(139, 188, 36, 22), Qt.AlignCenter, f"{self.total_items}个")


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()

        global PROFILE_FONT
        font_path = Path.home() / "Library" / "Fonts" / "乐米元气团团体.ttf"
        if font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                PROFILE_FONT = families[0]

        self.pet_size = 250
        self.base_path = Path(__file__).resolve().parent
        self.save_path = self.base_path / "pet_status.json"

        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.NoDropShadowWindowHint
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )
        self.setAcceptDrops(True)

        self.drag_start_global = QPoint()
        self.window_start_position = QPoint()
        self.is_dragging = False
        self.work_window_drag = False
        self.petting_click_active = False
        self.lifted_pixmap = None
        self.drag_anchor_window = QPoint()
        self.drag_pivot = QPoint()
        self.drag_label_x = 0
        self.drag_swing_phase = 0.0
        self.drag_swing_amplitude = 5
        self.drag_swing_speed = 2.5
        self.drag_timer = QTimer(self)
        self.drag_timer.setInterval(16)
        self.drag_timer.timeout.connect(self.update_drag_swing)
        self.session_elapsed = QElapsedTimer()
        self.session_elapsed.start()

        # ==================================================
        # 功能管理器
        # ==================================================

        self.animation_manager = AnimationManager(
            pet=self,
            base_path=self.base_path,
            pet_size=self.pet_size,
        )

        self.dialogue_manager = DialogueManager(
            self
        )

        self.status_manager = StatusManager(
            pet=self,
            save_path=self.save_path,
        )

        self.petting_manager = PettingManager(
            self
        )

        # 必须先创建 UI
        # 因为整点问候显示气泡时需要使用 pet_label
        self.setup_ui()
        application = QApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(
                self.status_manager.save_status
            )

        # UI 创建完成后，再启动整点问候
        self.hourly_greeting_manager = HourlyGreetingManager(
            pet=self,
            dialogue_manager=self.dialogue_manager,
        )

        self.dialogue_manager.update_position()

        self.animation_manager.start()
        self.status_manager.start()

        self.show()

        # ==================================================
        # 临时测试整点问候
        # 取消下一行前面的 #，运行后会立即显示 14 点台词
        # 测试成功后记得重新加上 #
        # ==================================================

        # 已注释：仅用于调试，发布前请保持注释状态
        # self.hourly_greeting_manager.test_greeting(14)

    # ==================================================
    # UI
    # ==================================================

    def setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignBottom)

        self.pet_label = QLabel()

        self.pet_label.setAlignment(
            Qt.AlignCenter
        )

        self.pet_label.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.pet_label.setFixedSize(
            self.pet_size,
            self.pet_size,
        )

        self.pet_label.installEventFilter(
            self
        )

        if self.animation_manager.idle_frames:
            self.pet_label.setPixmap(
                self.animation_manager.idle_frames[0]
            )
        else:
            self.pet_label.setText(
                "没有找到 Idle 序列帧"
            )

            self.pet_label.setStyleSheet(
                """
                color: red;
                background: white;
                border-radius: 10px;
                """
            )

        self.main_layout.addWidget(self.pet_label, alignment=Qt.AlignBottom)

        self.lifted_pixmap = self.load_lifted_pixmap()

        self.pet_hunger_overlay = QProgressBar(None)
        self.pet_hunger_overlay.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.pet_hunger_overlay.setAttribute(Qt.WA_TranslucentBackground)
        self.pet_hunger_overlay.setAttribute(Qt.WA_NoSystemBackground, True)
        self.pet_hunger_overlay.setAttribute(Qt.WA_ShowWithoutActivating)
        self.pet_hunger_overlay.setAttribute(
            Qt.WA_TransparentForMouseEvents
        )
        self.pet_hunger_overlay.setRange(0, 100)
        self.pet_hunger_overlay.setFixedSize(120, 15)
        self.pet_hunger_overlay.setAlignment(Qt.AlignCenter)
        self.pet_hunger_overlay.setTextVisible(True)
        self.pet_hunger_overlay.setStyleSheet(
            """
            QProgressBar {
                color: #557f2f;
                background: #e2d8c8;
                border: 1px solid #ffffff;
                border-radius: 7px;
                font-family: "Noto Sans";
                font-size: 8px;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background: #94d936;
                border-radius: 6px;
            }
            """
        )
        self.pet_hunger_overlay.hide()
        self.pet_hunger_overlay_timer = QTimer(self)
        self.pet_hunger_overlay_timer.setSingleShot(True)
        self.pet_hunger_overlay_timer.setInterval(2000)
        self.pet_hunger_overlay_timer.timeout.connect(
            self.hide_pet_hunger_overlay
        )

        self.hunger_gain_label = QLabel(self)
        self.hunger_gain_label.setFixedSize(100, 28)
        self.hunger_gain_label.setAlignment(Qt.AlignCenter)
        self.hunger_gain_label.setAttribute(
            Qt.WA_TransparentForMouseEvents
        )
        self.hunger_gain_label.setStyleSheet(
            f"""
            color: #79bd27;
            background: transparent;
            font-family: "{PROFILE_FONT}";
            font-size: 16px;
            font-weight: bold;
            """
        )
        self.hunger_gain_opacity = QGraphicsOpacityEffect(
            self.hunger_gain_label
        )
        self.hunger_gain_label.setGraphicsEffect(
            self.hunger_gain_opacity
        )
        self.hunger_gain_animation = QParallelAnimationGroup(self)
        self.hunger_gain_move_animation = QPropertyAnimation(
            self.hunger_gain_label,
            b"pos",
        )
        self.hunger_gain_move_animation.setDuration(1200)
        self.hunger_gain_move_animation.setEasingCurve(
            QEasingCurve.OutCubic
        )
        self.hunger_gain_fade_animation = QPropertyAnimation(
            self.hunger_gain_opacity,
            b"opacity",
        )
        self.hunger_gain_fade_animation.setDuration(1200)
        self.hunger_gain_fade_animation.setStartValue(1.0)
        self.hunger_gain_fade_animation.setEndValue(0.0)
        self.hunger_gain_animation.addAnimation(
            self.hunger_gain_move_animation
        )
        self.hunger_gain_animation.addAnimation(
            self.hunger_gain_fade_animation
        )
        self.hunger_gain_animation.finished.connect(
            self.hunger_gain_label.hide
        )
        self.hunger_gain_label.hide()

        # ==================================================
        # 状态面板
        # ==================================================

        self.status_panel = QWidget()
        self.status_panel.setObjectName("statusPanel")
        self.status_panel.setFixedSize(ProfilePage.WIDTH, ProfilePage.HEIGHT)
        panel_layout = QVBoxLayout(self.status_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        self.status_stack = QStackedWidget()
        panel_layout.addWidget(self.status_stack)

        # 主状态页面
        ui_root = self.base_path / "assets" / "ui" / "profile"
        self.main_status_page = ProfilePage(ui_root)
        portrait = QLabel(self.main_status_page)
        portrait.setGeometry(39, 109, 89, 113)
        portrait.setAlignment(Qt.AlignCenter)
        portrait.setPixmap(
            load_hidpi_pixmap(
                ui_root / "Photo" / "Photo.png",
                89,
                113,
            )
        )

        for index in range(5):
            star = QLabel(self.main_status_page)
            star.setGeometry(40 + index * 17, 210, 17, 17)
            star_name = (
                "State=Filled.png" if index == 0 else "State=Empty.png"
            )
            star.setAlignment(Qt.AlignCenter)
            star.setPixmap(
                load_hidpi_pixmap(
                    ui_root / "star" / star_name,
                    17,
                    17,
                )
            )

        rows = [
            ("EXP", "经验值", "Icon - EXP.png", 2000, 1500),
            ("Mood", "心 情", "Icon - Mood.png", 100, self.status_manager.mood),
            ("Food", "饱 腹", "Icon - Food.png", 100, self.status_manager.hunger),
            ("Tired", "疲 劳", "Icon - Tired.png", 100, 80),
        ]
        self.profile_bars = {}
        for row, (key, text, icon_name, maximum, value) in enumerate(rows):
            y = 101 + row * 24
            icon = QLabel(self.main_status_page)
            icon.setGeometry(153, y - 4, 35, 26)
            icon.setAlignment(Qt.AlignCenter)
            icon_height = 17 if key in {"EXP", "Mood"} else 22
            icon_max_width = 28 if key in {"EXP", "Mood"} else 35
            icon.setPixmap(
                load_hidpi_icon(
                    ui_root / "icons" / icon_name,
                    height=icon_height,
                    max_width=icon_max_width,
                )
            )
            label = QLabel(text, self.main_status_page)
            label.setGeometry(188, y - 2, 52, 23)
            label.setStyleSheet(
                f"color:#80613c; font-family:'{PROFILE_FONT}'; "
                "font-size:15px; font-weight:bold;"
            )
            bar = ProfileProgressBar(maximum, self.main_status_page)
            bar.setGeometry(242, y, 109, 15)
            bar.setValue(value)
            self.profile_bars[key] = bar
        self.mood_bar = self.profile_bars["Mood"]
        self.hunger_bar = self.profile_bars["Food"]

        time_icon = QLabel(self.main_status_page)
        time_icon.setGeometry(153, 194, 35, 26)
        time_icon.setAlignment(Qt.AlignCenter)
        time_icon.setPixmap(
            load_hidpi_icon(
                ui_root / "icons" / "Icon - Time.png",
                height=23,
                max_width=32,
            )
        )
        time_label = QLabel("陪伴时间", self.main_status_page)
        time_label.setGeometry(188, 196, 70, 23)
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setStyleSheet(
            f"color:#80613c; font-family:'{PROFILE_FONT}'; "
            "font-size:15px; font-weight:bold;"
        )
        self.companion_label = QLabel(self.main_status_page)
        self.companion_label.setGeometry(262, 196, 80, 23)
        self.companion_label.setAlignment(Qt.AlignCenter)
        self.companion_label.setStyleSheet(
            f"color:#e46f61; font-family:'{PROFILE_FONT}'; "
            "font-size:15px; font-weight:bold;"
        )
        self.update_companion_time()
        self.companion_timer = QTimer(self)
        self.companion_timer.setInterval(1000)
        self.companion_timer.timeout.connect(self.update_companion_time)
        self.companion_timer.start()

        self.shop_button = QPushButton("商店", self.main_status_page)
        self.shop_button.setObjectName("shopButton")
        self.shop_button.setGeometry(164, 230, 83, 28)
        self.feed_button = QPushButton("背包", self.main_status_page)
        self.feed_button.setObjectName("bagButton")
        self.feed_button.setGeometry(257, 230, 83, 28)
        self.feed_button.clicked.connect(self.open_food_page)
        self.shop_button.clicked.connect(self.open_shop_page)

        self.coin_label = QLabel(self.main_status_page)
        self.coin_label.hide()
        self.status_stack.addWidget(self.main_status_page)

        # 商店页面
        shop_root = self.base_path / "assets" / "ui" / "shop"
        self.shop_page = ShopPage(shop_root)
        self.shop_page.itemSelected.connect(self.select_shop_item)
        self.shop_page.purchaseRequested.connect(
            self.buy_selected_shop_item
        )
        self.shop_page.backRequested.connect(
            self.show_main_status_page
        )
        self.status_stack.addWidget(self.shop_page)
        self.shop_page.back_button.setParent(self)
        self.shop_page.back_button.hide()

        # 食物选择页面
        self.food_page = QWidget()
        food_layout = QVBoxLayout(self.food_page)
        food_layout.setContentsMargins(0, 0, 0, 0)
        food_layout.setSpacing(7)

        food_title = QLabel("选择食物")
        food_title.setAlignment(Qt.AlignCenter)
        food_item_label = QLabel("🍎 苹果")
        food_item_label.setAlignment(Qt.AlignCenter)
        self.food_apple_count_label = QLabel()
        self.food_apple_count_label.setAlignment(Qt.AlignCenter)
        self.food_message_label = QLabel()
        self.food_message_label.setAlignment(Qt.AlignCenter)
        self.feed_apple_button = QPushButton("喂食")
        self.food_back_button = QPushButton("返回")

        self.feed_apple_button.clicked.connect(
            self.feed_apple_from_food
        )
        self.food_back_button.clicked.connect(
            self.show_main_status_page
        )

        food_layout.addWidget(food_title)
        food_layout.addWidget(food_item_label)
        food_layout.addWidget(self.food_apple_count_label)
        food_layout.addWidget(self.food_message_label)
        food_layout.addWidget(self.feed_apple_button)
        food_layout.addWidget(self.food_back_button)
        self.status_stack.addWidget(self.food_page)
        self.status_stack.setCurrentWidget(self.main_status_page)
        self.status_stack.setFixedSize(ProfilePage.WIDTH, ProfilePage.HEIGHT)

        self.status_panel_positioner = QWidget()
        self.status_panel_positioner.setFixedSize(
            ProfilePage.WIDTH,
            ProfilePage.HEIGHT,
        )
        positioner_layout = QVBoxLayout(self.status_panel_positioner)
        positioner_layout.setContentsMargins(0, 0, 0, 0)
        positioner_layout.setSpacing(0)
        positioner_layout.addWidget(
            self.status_panel,
            alignment=Qt.AlignTop,
        )
        self.main_layout.addWidget(
            self.status_panel_positioner,
            alignment=Qt.AlignBottom,
        )

        self.status_panel.hide()
        self.status_panel_positioner.hide()

        self.setStyleSheet(
            """
            QWidget#statusPanel {
                background: transparent;
            }

            QLabel {
                color: #444444;
                font-family: "乐米元气团团体";
                font-size: 15px;
            }

            QPushButton {
                background-color: #ef7569;
                color: white;
                border: 2px solid #d95e52;
                border-radius: 12px;
                font-family: "乐米元气团团体";
                font-size: 15px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #f3867b;
            }

            QPushButton:pressed {
                background-color: #d95e52;
            }

            QPushButton#bagButton {
                background-color: #f4aa3e;
                border-color: #df8d16;
            }

            QPushButton#bagButton:hover {
                background-color: #f7b653;
            }

            QPushButton#bagButton:pressed {
                background-color: #df8d16;
            }
            """
        )

        self.setFixedSize(self.pet_size + 16, self.pet_size + 16)
        self.update_drag_anchor_window()

    # ==================================================
    # 鼠标与菜单
    # ==================================================

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(SHOP_DRAG_MIME):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if (
            event.mimeData().hasFormat(SHOP_DRAG_MIME)
            and self.pet_label.geometry().contains(
                event.position().toPoint()
            )
        ):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        if (
            not event.mimeData().hasFormat(SHOP_DRAG_MIME)
            or not self.pet_label.geometry().contains(
                event.position().toPoint()
            )
        ):
            event.ignore()
            return
        item_id = bytes(
            event.mimeData().data(SHOP_DRAG_MIME)
        ).decode("utf-8")
        if item_id not in SHOP_ITEM_MAP:
            event.ignore()
            return
        if self.status_manager.feed_shop_item(
            item_id,
            SHOP_HUNGER_VALUES[item_id],
            SHOP_ITEM_MAP[item_id][1],
        ):
            self.show_pet_hunger_overlay()
            self.show_hunger_gain_text(
                self.status_manager.last_feed_amount
            )
            event.acceptProposedAction()
            return
        event.ignore()

    def show_pet_hunger_overlay(self):
        self.pet_hunger_overlay.setValue(self.status_manager.hunger)
        self.pet_hunger_overlay.setFormat(
            f"饱腹 {self.status_manager.hunger}%"
        )
        self.update_pet_hunger_overlay_position()
        self.dialogue_manager.set_stacked_offset(
            self.pet_hunger_overlay.height() + 4
        )
        self.update_pet_hunger_overlay_position()
        self.pet_hunger_overlay.show()
        self.pet_hunger_overlay.raise_()
        self.pet_hunger_overlay_timer.start()

    def update_pet_hunger_overlay_position(self):
        if not hasattr(self, "pet_hunger_overlay"):
            return
        pet_position = self.pet_label.mapToGlobal(QPoint(0, 0))
        self.pet_hunger_overlay.move(
            pet_position.x()
            + (self.pet_label.width() - self.pet_hunger_overlay.width()) // 2,
            pet_position.y() - self.pet_hunger_overlay.height(),
        )

    def hide_pet_hunger_overlay(self):
        self.pet_hunger_overlay.hide()
        self.dialogue_manager.set_stacked_offset(0)

    def show_hunger_gain_text(self, amount):
        amount = max(0, int(amount))
        if amount <= 0:
            return
        self.main_layout.activate()
        pet_position = self.pet_label.mapTo(self, QPoint(0, 0))
        start_position = QPoint(
            pet_position.x() + self.pet_label.width() // 2 + 28,
            pet_position.y() + self.pet_label.height() // 2 - 14,
        )
        end_position = start_position + QPoint(0, -60)
        self.hunger_gain_animation.stop()
        self.hunger_gain_label.setText(f"饱腹 +{amount}%")
        self.hunger_gain_opacity.setOpacity(1.0)
        self.hunger_gain_label.move(start_position)
        self.hunger_gain_label.show()
        self.hunger_gain_label.raise_()
        self.hunger_gain_move_animation.setStartValue(start_position)
        self.hunger_gain_move_animation.setEndValue(end_position)
        self.hunger_gain_animation.start()

    def eventFilter(
        self,
        watched,
        event,
    ):
        if watched is self.pet_label:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.petting_click_active = (
                        self.animation_manager.is_petting()
                    )
                    self.drag_start_global = (
                        event.globalPosition().toPoint()
                    )

                    self.window_start_position = (
                        self.pos()
                    )

                    self.is_dragging = False
                    self.work_window_drag = (
                        self.animation_manager.current_state == "work"
                    )

                    event.accept()

                    return True

                if event.button() == Qt.RightButton:
                    self.show_context_menu(
                        event.globalPosition().toPoint()
                    )

                    event.accept()

                    return True

            elif event.type() == QEvent.MouseMove:
                if event.buttons() & Qt.LeftButton:
                    if self.petting_click_active:
                        event.accept()
                        return True

                    current_global = (
                        event.globalPosition().toPoint()
                    )

                    movement = (
                        current_global
                        - self.drag_start_global
                    )

                    if movement.manhattanLength() > 5:
                        if not self.is_dragging:
                            self.is_dragging = True
                            if not self.work_window_drag:
                                self.start_drag()

                    if self.is_dragging:
                        self.current_drag_global = current_global
                        if self.work_window_drag:
                            self.move(
                                self.window_start_position
                                + movement
                            )
                        else:
                            self.move_drag_anchor_to_mouse(
                                self.current_drag_global
                            )
                            if not self.drag_timer.isActive():
                                self.drag_timer.start()
                            if hasattr(self, "activity_trigger_manager"):
                                self.activity_trigger_manager._register_drag_motion()

                    event.accept()

                    return True

            elif event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    if self.petting_click_active:
                        local_position = event.position().toPoint()
                        if self.petting_manager.is_head_position(
                            local_position
                        ):
                            self.petting_manager.register_head_click()
                        else:
                            self.toggle_status_panel()
                        self.petting_click_active = False
                        self.is_dragging = False
                        event.accept()
                        return True

                    if self.work_window_drag:
                        if not self.is_dragging:
                            local_position = (
                                event.position().toPoint()
                            )
                            if self.petting_manager.is_head_position(
                                local_position
                            ):
                                self.dialogue_manager.show_message(
                                    "等等，我先看完这个文件",
                                    duration=3500,
                                    allow_during_work=True,
                                )
                        self.is_dragging = False
                        self.work_window_drag = False
                        event.accept()
                        return True

                    if self.is_dragging:
                        self.drag_timer.stop()
                        self.drag_swing_phase = 0.0
                        self.move_drag_anchor_to_mouse(
                            self.current_drag_global
                        )
                        self.stop_drag()
                    else:
                        local_position = (
                            event.position().toPoint()
                        )

                        if self.petting_manager.is_head_position(
                            local_position
                        ):
                            self.petting_manager.register_head_click()
                        else:
                            self.toggle_status_panel()

                    self.is_dragging = False
                    self.work_window_drag = False

                    event.accept()

                    return True

        return super().eventFilter(
            watched,
            event,
        )

    def start_drag(self):
        if self.is_interaction_locked():
            return
        self.animation_manager.pause_for_drag()
        if self.lifted_pixmap is not None:
            rotated = self.render_rotated_lifted_pixmap(0.0)
            self.pet_label.setPixmap(rotated)
            self.pet_label.update()

    def stop_drag(self):
        if self.is_interaction_locked():
            return
        self.animation_manager.resume_idle()

    def update_drag_swing(self):
        if (
            not self.is_dragging
            or self.is_interaction_locked()
        ):
            self.drag_timer.stop()
            return

        self.drag_swing_phase += (
            self.drag_swing_speed
            * self.drag_timer.interval()
            / 1000.0
        )
        angle = (
            self.drag_swing_amplitude
            * math.sin(self.drag_swing_phase)
        )
        if self.lifted_pixmap is not None:
            rotated = self.render_rotated_lifted_pixmap(angle)
            self.pet_label.setPixmap(rotated)
            self.pet_label.update()

    def render_rotated_lifted_pixmap(self, angle: float):
        if self.lifted_pixmap is None:
            return self.animation_manager.idle_frames[0]

        ratio = self.animation_manager.device_pixel_ratio
        physical_size = round(self.pet_size * ratio)
        canvas = QPixmap(physical_size, physical_size)
        canvas.fill(Qt.transparent)
        canvas.setDevicePixelRatio(ratio)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        transform = QTransform()
        transform.translate(
            self.drag_pivot.x(),
            self.drag_pivot.y(),
        )
        transform.rotate(angle)
        transform.translate(
            -self.drag_pivot.x(),
            -self.drag_pivot.y(),
        )
        painter.setTransform(transform)
        painter.drawPixmap(self.drag_label_x, 0, self.lifted_pixmap)
        painter.end()

        return canvas

    def load_lifted_pixmap(self):
        lifted_path = self.base_path / "assets" / "lifted" / "lifted.png"
        pixmap = QPixmap(str(lifted_path))
        if pixmap.isNull():
            print(f"无法读取 lifted 图像：{lifted_path}")
            return None

        ratio = self.animation_manager.device_pixel_ratio
        physical_size = round(self.pet_size * ratio)
        scaled = pixmap.scaled(
            physical_size,
            physical_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(ratio)
        logical_width = scaled.width() / ratio
        logical_height = scaled.height() / ratio

        pivot = QPoint(
            round(logical_width * 603 / pixmap.width()),
            round(logical_height * 150 / pixmap.height()),
        )
        self.drag_label_x = (
            self.pet_size - logical_width
        ) // 2
        self.drag_label_x = round(self.drag_label_x)
        self.drag_pivot = QPoint(
            self.drag_label_x + pivot.x(),
            pivot.y(),
        )
        self.update_drag_anchor_window()

        return scaled

    def update_drag_anchor_window(self):
        if not hasattr(self, "pet_label"):
            return
        label_pos = self.pet_label.pos()
        self.drag_anchor_window = QPoint(
            label_pos.x() + self.drag_pivot.x(),
            label_pos.y() + self.drag_pivot.y(),
        )

    def move_drag_anchor_to_mouse(self, mouse_global_position):
        """按红点当前的真实屏幕坐标移动窗口，使其与鼠标重合。"""
        anchor_global_position = self.pet_label.mapToGlobal(
            self.drag_pivot
        )
        self.move(
            self.pos()
            + mouse_global_position
            - anchor_global_position
        )

    def refresh_economy_ui(self):
        """统一刷新主状态、商店和食物页面的金币与库存。"""
        manager = self.status_manager
        coin_count = max(0, manager.coin_count)
        apple_count = max(0, manager.apple_count)
        interaction_enabled = not self.is_economy_interaction_locked()

        self.coin_label.setText(f"🪙 × {coin_count}")
        self.food_apple_count_label.setText(f"持有：{apple_count}")

        self.feed_button.setEnabled(interaction_enabled)
        self.shop_button.setEnabled(interaction_enabled)
        selected_id = self.shop_page.selected_item_id
        selected_price = SHOP_ITEM_MAP[selected_id][2]
        self.shop_page.set_economy(
            coin_count,
            manager.total_inventory_count(),
            interaction_enabled
            and manager.can_afford(selected_price),
        )
        self.feed_apple_button.setEnabled(
            interaction_enabled
            and apple_count > 0
            and manager.hunger < 100
        )

        if apple_count == 0:
            self.food_message_label.setText(
                "没有苹果了，去商店买一个吧。"
            )
        elif manager.hunger >= 100:
            self.food_message_label.setText("已经吃得饱饱的啦～")
        elif self.food_message_label.text() in (
            "没有苹果了，去商店买一个吧。",
            "已经吃得饱饱的啦～",
        ):
            self.food_message_label.clear()

    def update_companion_time(self):
        """Display persisted companionship plus the current session."""
        elapsed_minutes = int(
            self.get_total_companion_seconds() // 60
        )
        self.companion_label.setText(f"{elapsed_minutes} 分钟")

    def get_total_companion_seconds(self):
        return max(
            0.0,
            self.status_manager.companion_seconds
            + self.session_elapsed.elapsed() / 1000.0,
        )

    def open_shop_page(self):
        if self.is_economy_interaction_locked():
            return
        self.refresh_economy_ui()
        self.resize_status_content(
            ShopPage.WIDTH,
            ShopPage.HEIGHT,
        )
        self.status_stack.setCurrentWidget(self.shop_page)
        self.main_layout.activate()
        self.shop_page.back_button.move(
            self.status_panel.mapTo(self, QPoint(-17, 27))
        )
        self.shop_page.back_button.show()
        self.shop_page.back_button.raise_()

    def open_food_page(self):
        if self.is_economy_interaction_locked():
            return
        self.shop_page.back_button.hide()
        self.food_message_label.clear()
        self.refresh_economy_ui()
        self.resize_status_content(
            ProfilePage.WIDTH,
            ProfilePage.HEIGHT,
        )
        self.status_stack.setCurrentWidget(self.food_page)

    def show_main_status_page(self):
        if self.is_economy_interaction_locked():
            return
        self.shop_page.back_button.hide()
        self.refresh_economy_ui()
        self.resize_status_content(
            ProfilePage.WIDTH,
            ProfilePage.HEIGHT,
        )
        self.status_stack.setCurrentWidget(self.main_status_page)

    def resize_status_content(self, width, height):
        """Resize a stacked page while keeping the pet fixed on screen."""
        pet_global_position = self.pet_label.mapToGlobal(QPoint(0, 0))
        self.status_stack.setFixedSize(width, height)
        self.status_panel.setFixedSize(width, height)
        self.status_panel_positioner.setFixedSize(width, height)
        if self.status_panel.isVisible():
            self.setFixedSize(
                self.pet_size + width + 16,
                max(self.pet_size, height) + 16,
            )
            self.preserve_pet_global_position(pet_global_position)
            self.dialogue_manager.update_position()
            self.keep_inside_screen()

    def select_shop_item(self, item_id):
        self.shop_page.select_item(item_id)
        self.refresh_economy_ui()

    def buy_selected_shop_item(self):
        if self.is_economy_interaction_locked():
            return
        item_id = self.shop_page.selected_item_id
        price = SHOP_ITEM_MAP[item_id][2]
        self.status_manager.buy_item(
            item_id,
            price,
        )
        self.refresh_economy_ui()

    def feed_apple_from_food(self):
        if self.is_economy_interaction_locked():
            return
        feeding_succeeded = self.status_manager.feed_with_apple()
        self.refresh_economy_ui()
        if feeding_succeeded:
            self.food_message_label.setText("喂食成功")
        elif self.status_manager.apple_count <= 0:
            self.food_message_label.setText(
                "没有苹果了，去商店买一个吧。"
            )
        elif self.status_manager.hunger >= 100:
            self.food_message_label.setText("已经吃得饱饱的啦～")

    def collapse_status_panel_for_work(self):
        """进入 work 时收起状态栏，不触发普通交互逻辑。"""
        if not self.status_panel.isVisible():
            return
        self.shop_page.back_button.hide()
        pet_global_position = self.pet_label.mapToGlobal(QPoint(0, 0))
        self.status_panel.hide()
        self.status_panel_positioner.hide()
        self.status_stack.setCurrentWidget(self.main_status_page)
        self.setFixedSize(self.pet_size + 16, self.pet_size + 16)
        self.preserve_pet_global_position(pet_global_position)
        self.dialogue_manager.update_position()
        self.keep_inside_screen()

    def toggle_status_panel(self):
        if self.is_economy_interaction_locked():
            return
        pet_global_position = self.pet_label.mapToGlobal(QPoint(0, 0))
        if self.status_panel.isVisible():
            self.shop_page.back_button.hide()
            self.status_panel.hide()
            self.status_panel_positioner.hide()
            self.setFixedSize(self.pet_size + 16, self.pet_size + 16)
        else:
            self.show_main_status_page()
            self.status_panel_positioner.show()
            self.status_panel.show()
            self.setFixedSize(
                self.pet_size + ProfilePage.WIDTH + 16,
                max(
                    self.pet_size,
                    ProfilePage.HEIGHT,
                ) + 16,
            )

        self.preserve_pet_global_position(pet_global_position)
        self.dialogue_manager.update_position()

        self.keep_inside_screen()

    def preserve_pet_global_position(self, previous_global_position):
        """Compensate window resizing so the pet stays still on screen."""
        self.main_layout.activate()
        current_global_position = self.pet_label.mapToGlobal(QPoint(0, 0))
        self.move(
            self.pos()
            + previous_global_position
            - current_global_position
        )

    def is_interaction_locked(self):
        return self.animation_manager.is_interaction_locked()

    def is_economy_interaction_locked(self):
        """工作状态锁定商店和喂食；摸头动画期间保持可操作。"""
        return self.animation_manager.current_state == "work"

    def show_context_menu(
        self,
        global_position,
    ):
        menu = QMenu(self)

        toggle_action = QAction(
            "显示／隐藏状态",
            self,
        )

        toggle_action.triggered.connect(
            self.toggle_status_panel
        )

        cancel_work_action = None
        if self.animation_manager.current_state == "work":
            cancel_work_action = QAction("退出工作", self)
            cancel_work_action.triggered.connect(
                self.animation_manager.cancel_work
            )

        quit_action = QAction(
            "退出桌宠",
            self,
        )

        quit_action.triggered.connect(
            QApplication.quit
        )

        menu.addAction(
            toggle_action
        )

        if cancel_work_action is not None:
            menu.addAction(cancel_work_action)

        menu.addSeparator()

        menu.addAction(
            quit_action
        )

        menu.exec(
            global_position
        )

    # ==================================================
    # 屏幕边界与关闭
    # ==================================================

    def keep_inside_screen(self):
        screen = QGuiApplication.screenAt(
            self.frameGeometry().center()
        )

        if screen is None:
            screen = QGuiApplication.primaryScreen()

        available = screen.availableGeometry()

        new_x = min(
            max(
                self.x(),
                available.left(),
            ),
            available.right()
            - self.width()
            + 1,
        )

        new_y = min(
            max(
                self.y(),
                available.top(),
            ),
            available.bottom()
            - self.height()
            + 1,
        )

        self.move(
            new_x,
            new_y,
        )

    def closeEvent(
        self,
        event,
    ):
        self.status_manager.save_status()

        event.accept()


def run():
    app = QApplication(
        sys.argv
    )

    pet = DesktopPet()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    run()
