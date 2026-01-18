"""Widget PyQt5: Zbiornik o nieregularnym ksztalcie (agregacja grafiki).

Klasa i struktura zgodna z projekt_09.pdf: class Zbiornik(QWidget).
"""

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QFont
from PyQt5.QtWidgets import QWidget


class Zbiornik(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(220, 260)

        self.top_trapez_h = 40
        self.rect_h = 140
        self.bot_trapez_h = 40

        self.width_top = 140
        self.width_mid = 100
        self.width_bot = 30

        self.total_tank_height = self.top_trapez_h + self.rect_h + self.bot_trapez_h

        self._poziom = 0.0
        self._temp = 20.0
        self._name = ""

        self.draw_x = 20
        self.draw_y = 20

    def setPoziom(self, poziom: float) -> None:
        self._poziom = max(0.0, min(1.0, float(poziom)))
        self.update()

    def setPolozenie(self, x: int, y: int) -> None:
        self.draw_x = int(x)
        self.draw_y = int(y)
        self.update()

    def setName(self, name: str) -> None:
        self._name = str(name)
        self.update()

    def setTemp(self, temp_c: float) -> None:
        self._temp = float(temp_c)
        self.update()

    def getPoziom(self) -> float:
        return self._poziom

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.draw_x + (self.width_top / 2.0)
        start_y = self.draw_y

        path = QPainterPath()

        p1_tl = QPointF(cx - self.width_top / 2, start_y)
        p1_tr = QPointF(cx + self.width_top / 2, start_y)
        p2_ml = QPointF(cx - self.width_mid / 2, start_y + self.top_trapez_h)
        p2_mr = QPointF(cx + self.width_mid / 2, start_y + self.top_trapez_h)
        p3_bl = QPointF(cx - self.width_mid / 2, start_y + self.top_trapez_h + self.rect_h)
        p3_br = QPointF(cx + self.width_mid / 2, start_y + self.top_trapez_h + self.rect_h)
        p4_bl = QPointF(cx - self.width_bot / 2, start_y + self.total_tank_height)
        p4_br = QPointF(cx + self.width_bot / 2, start_y + self.total_tank_height)

        path.moveTo(p1_tl)
        path.lineTo(p1_tr)
        path.lineTo(p2_mr)
        path.lineTo(p3_br)
        path.lineTo(p4_br)
        path.lineTo(p4_bl)
        path.lineTo(p3_bl)
        path.lineTo(p2_ml)
        path.closeSubpath()

        painter.save()
        painter.setClipPath(path)
        liquid_height_px = self.total_tank_height * self._poziom
        rect_liquid = QRectF(
            cx - self.width_top / 2,
            start_y + self.total_tank_height - liquid_height_px,
            self.width_top,
            liquid_height_px,
        )
        painter.fillRect(rect_liquid, QColor(0, 120, 255, 180))
        painter.restore()

        pen = QPen(Qt.gray, 3)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        painter.setPen(Qt.white)
        painter.setFont(QFont('Arial', 10))
        if self._name:
            painter.drawText(self.draw_x, self.draw_y - 6, self._name)
        painter.drawText(self.draw_x, self.draw_y + self.total_tank_height + 18, f"{self._poziom*100:.0f}%  {self._temp:.1f}C")
