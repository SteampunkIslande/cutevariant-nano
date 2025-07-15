# Qt imports
from PySide6.QtCore import QModelIndex, QRect, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem


class Formatter(object):
    """Helper to customize cell style from QueryModel.
    You can set the font, background, foreground and decoration (QIcon)

    Class attributes:
        - DISPLAY_NAME: Name of the formatter displayed on the GUI.
    """

    DISPLAY_NAME = "No formatter"

    def refresh(self):
        pass

    def format(
        self, field: str, value: str, row_dict: dict, option, is_selected: bool = False
    ):

        return {"text": str(value)}


class FormatterDelegate(QStyledItemDelegate):
    """Specify the aesthetic (style and color) of variants displayed on a view"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._formatter = None

    def set_formatter(self, formatter: Formatter):
        self._formatter = formatter

    def color_mix(self, color1: QColor, color2: QColor, ratio: float) -> QColor:
        """Mix two colors with a ratio"""
        r = int(color1.red() * (1 - ratio) + color2.red() * ratio)
        g = int(color1.green() * (1 - ratio) + color2.green() * ratio)
        b = int(color1.blue() * (1 - ratio) + color2.blue() * ratio)
        return QColor(r, g, b)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        """Paint with formatter if defined"""

        if self._formatter is None:
            return super().paint(painter, option, index)

        # Get row data
        row_dict = index.data(Qt.ItemDataRole.UserRole)

        # Draw selections
        if option.state & QStyle.StateFlag.State_Enabled:
            bg = (
                QPalette.ColorGroup.Normal
                if option.state & QStyle.StateFlag.State_Active
                or option.state & QStyle.StateFlag.State_Selected
                else QPalette.ColorGroup.Inactive
            )
        else:
            bg = QPalette.ColorGroup.Disabled

        field_name = index.model().headerData(
            index.column(), Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
        )
        field_value = index.data(Qt.ItemDataRole.DisplayRole)
        is_selected = option.state & QStyle.StateFlag.State_Selected
        style = self._formatter.format(
            field_name, field_value, row_dict, option, is_selected
        )

        font = style.get("font", QFont())
        text = style.get("text", str(field_value))
        icon = style.get("icon", None)
        color = style.get("color")
        bg_color: QColor = style.get("background", None)
        is_bold = style.get("bold", False)
        is_italic = style.get("italic", False)

        if icon is not None:
            text = ""  # If an icon is set, do not display text

        if is_bold:
            font.setBold(True)
        else:
            font.setBold(False)

        if is_italic:
            font.setItalic(True)
        else:
            font.setItalic(False)

        if bg_color is not None:
            if is_selected:
                bg_color = self.color_mix(
                    bg_color,
                    option.palette.color(bg, QPalette.ColorRole.Highlight),
                    0.25,
                )
            else:
                bg_color = self.color_mix(
                    bg_color, option.palette.color(bg, QPalette.ColorRole.Base), 0.25
                )
            painter.fillRect(option.rect, bg_color)
        else:
            if is_selected:
                bg_color = option.palette.color(bg, QPalette.ColorRole.Highlight)
            else:
                bg_color = option.palette.color(bg, QPalette.ColorRole.Base)
            painter.fillRect(option.rect, bg_color)

        if color is None:
            color = option.palette.color(
                QPalette.ColorRole.BrightText
                if is_selected
                else QPalette.ColorRole.Text
            )

        text_align = style.get(
            "text-align", Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        icon_align = style.get("icon-align", Qt.AlignmentFlag.AlignCenter)

        pixmap: QPixmap = style.get("pixmap", None)
        link = style.get("link", None)

        if pixmap:
            painter.drawPixmap(
                option.rect.x(),
                option.rect.y(),
                pixmap.width(),
                pixmap.height(),
                pixmap,
            )
            return

        if link:
            self.draw_url(painter, option.rect, text, text_align)
            return

        if icon:
            self.draw_icon(painter, option.rect, icon, icon_align)

        text_rec = option.rect.adjusted(3, 0, 0, 0)
        # Get text size
        bounding_box = option.fontMetrics.boundingRect(text_rec, text_align, text)

        if bounding_box.width() > text_rec.width():
            # If text is too long, truncate it
            text = option.fontMetrics.elidedText(
                text, Qt.TextElideMode.ElideRight, text_rec.width()
            )

        painter.setFont(font)
        painter.setPen(QPen(color))
        painter.drawText(option.rect.adjusted(3, 0, 0, 0), text_align, text)

    def draw_icon(
        self,
        painter: QPainter,
        rect: QRect,
        icon: QIcon,
        alignement=Qt.AlignmentFlag.AlignCenter,
    ):
        r = QRect(0, 0, rect.height(), rect.height())
        r.moveCenter(rect.center())

        if alignement & Qt.AlignmentFlag.AlignLeft:
            r.moveLeft(rect.left())

        if alignement & Qt.AlignmentFlag.AlignRight:
            r.moveRight(rect.right())

        painter.drawPixmap(r, icon.pixmap(r.width(), r.height()))

    def draw_url(
        self,
        painter: QPainter,
        rect: QRect,
        value: str,
        align=Qt.AlignmentFlag.AlignLeft,
    ):
        font = QFont()
        font.setUnderline(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor("blue")))
        painter.drawText(rect, align, value)
