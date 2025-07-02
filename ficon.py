# Qt imports


import logging

from PySide6.QtCore import QBuffer, QByteArray, QPoint, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QIconEngine,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication

# Custom imports


LOGGER = logging.getLogger(__name__)


class FIconEngine(QIconEngine):
    """Base class for FIcon; used to load custom font"""

    # Class attribute
    font = None

    def __init__(self):
        super().__init__()

        if QApplication.instance():
            self.palette = QApplication.instance().palette()
        else:
            self.palette = QPalette()

        self.color = None
        self.bgcolor = None

    def setCharacter(self, hex_character: int):
        self.hex_character = hex_character

    def setColor(self, color: QColor):
        self.color = color

    def setBackgroundColor(self, color: QColor):
        self.bgcolor = color

    def paint(
        self, painter: QPainter, rect: QRect, mode: QIcon.Mode, state: QIcon.State
    ):
        """override"""
        font = FIconEngine.font if hasattr(FIconEngine, "font") else painter.font()

        # The following test is to avoid crash when running python widget outside the __main__.my
        if not font:
            font = painter.font()
            return

        painter.save()

        #  draw background
        if self.bgcolor:
            painter.setBrush(QColor(self.bgcolor))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect)

        if self.color:
            painter.setPen(QPen(self.color))

        else:
            if mode == QIcon.Mode.Disabled:
                painter.setPen(
                    QPen(
                        self.palette.color(
                            QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText
                        )
                    )
                )
            else:
                painter.setPen(
                    QPen(
                        self.palette.color(
                            QPalette.ColorGroup.Active, QPalette.ColorRole.ButtonText
                        )
                    )
                )

        font.setPixelSize(rect.size().width())

        painter.setFont(font)
        # painter.setRenderHint(QPainter.HighQualityAntialiasing, True)

        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            str(chr(self.hex_character)),
        )
        painter.restore()

    def pixmap(self, size, mode, state):
        pix = QPixmap(size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        self.paint(painter, QRect(QPoint(0, 0), size), mode, state)
        return pix

    @classmethod
    def setFontPath(cls, filename):
        """Set font from a font file and return it

        :return: QFont or False if the file is not loaded
        """
        db = QFontDatabase()
        font_id = db.addApplicationFont(filename)
        if font_id == -1:
            LOGGER.error("FIconEngine:setFontPath:: cannot load font icon.")
            return False

        cls.font = QFont(db.applicationFontFamilies(font_id)[0])
        return cls.font


class FIcon(QIcon):
    """Handy public class to load and use custom font in QIcons"""

    def __init__(
        self, hex_character: int, color: QColor = None, bgcolor: QColor = None
    ):
        """Build an icon with the given character and color from the current font

        Args:
            hex_character (int): Hexadecimal value of the wanted icon in the
                font loaded in internal FIconEngine.
                Please see https://pictogrammers.com/library/mdi/
                and https://cdn.materialdesignicons.com/5.4.55/ for the mapping
                between hex values and icons.
            color (QPalette/str): Color palette to be used by the icon.
        """
        self.engine = FIconEngine()

        if self.engine.font is None:  # Return empty QIcon
            super().__init__()
        else:
            self.engine.setCharacter(hex_character)
            self.engine.setColor(color)
            self.engine.setBackgroundColor(bgcolor)

            super().__init__(self.engine)

    def to_base64(self, w=32, h=32):
        """Return icon as base64 to make it work with html"""
        pix = self.pixmap(w, h)
        data = QByteArray()
        buff = QBuffer(data)
        pix.save(buff, "PNG")
        return data.toBase64().data().decode()


def setFontPath(filename):
    """Handy function to load font file

    .. note:: Fonts are supposed to be in cst.DIR_FONTS
    .. note:: This function is called only 1 time at the start of the program
    """
    return FIconEngine.setFontPath(filename)
