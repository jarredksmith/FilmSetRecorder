from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

FG = QColor('#DCE8F3')
MUTED = QColor('#8FA8BE')
BLUE = QColor('#58AFFF')
BLUE2 = QColor('#1E91FF')
GREEN = QColor('#56E39F')
RED = QColor('#FF4C5B')
YELLOW = QColor('#FFD15A')
DARK = QColor('#0B2238')


def _pen(color=FG, width: float = 4.0) -> QPen:
    pen = QPen(color, width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _canvas(size: int) -> tuple[QPixmap, QPainter, float]:
    size = max(12, int(size))
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    scale = size / 64.0
    p.scale(scale, scale)
    return pm, p, scale


def _poly(points):
    return QPolygonF([QPointF(float(x), float(y)) for x, y in points])


def icon_pixmap(name: str, size: int = 64) -> QPixmap:
    pm, p, _ = _canvas(size)
    n = (name or '').lower()
    p.setBrush(Qt.NoBrush)
    p.setPen(_pen(FG, 4))

    if n == 'record':
        p.setPen(Qt.NoPen); p.setBrush(RED); p.drawEllipse(QRectF(18,18,28,28))
    elif n == 'record_white':
        p.setPen(Qt.NoPen); p.setBrush(QColor('#FFFFFF')); p.drawEllipse(QRectF(18,18,28,28))
    elif n == 'stop':
        p.setPen(Qt.NoPen); p.setBrush(FG); p.drawRoundedRect(QRectF(19,19,26,26), 3, 3)
    elif n == 'play':
        p.setPen(Qt.NoPen); p.setBrush(FG); p.drawPolygon(_poly([(22,15),(49,32),(22,49)]))
    elif n == 'next':
        p.setPen(Qt.NoPen); p.setBrush(FG)
        p.drawPolygon(_poly([(12,16),(31,32),(12,48)])); p.drawPolygon(_poly([(28,16),(47,32),(28,48)]))
        p.drawRoundedRect(QRectF(49,16,4,32), 2, 2)
    elif n == 'circle':
        # A star is clearer than a ring for the production "circle take" action.
        pts=[]
        for i in range(10):
            a=math.radians(-90+i*36); r=20 if i%2==0 else 8.5
            pts.append((32+math.cos(a)*r,32+math.sin(a)*r))
        p.setPen(Qt.NoPen); p.setBrush(YELLOW); p.drawPolygon(_poly(pts))
    elif n in ('tracks','waveform'):
        p.setPen(_pen(BLUE, 4.5))
        xs=[12,19,26,32,38,45,52]; hs=[16,28,40,50,40,28,16]
        for x,h in zip(xs,hs): p.drawLine(QPointF(x,32-h/2), QPointF(x,32+h/2))
    elif n in ('input','mic'):
        p.setPen(_pen(FG,4)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(QRectF(23,9,18,29), 9, 9)
        p.drawArc(QRectF(17,22,30,27), 0, -180*16)
        p.drawLine(QPointF(32,49),QPointF(32,55)); p.drawLine(QPointF(24,55),QPointF(40,55))
    elif n in ('audio','monitor'):
        p.setPen(Qt.NoPen); p.setBrush(FG); p.drawPolygon(_poly([(10,27),(20,27),(34,17),(34,47),(20,37),(10,37)]))
        p.setPen(_pen(BLUE,3)); p.setBrush(Qt.NoBrush); p.drawArc(QRectF(29,21,19,22), -60*16, 120*16); p.drawArc(QRectF(27,16,29,32), -60*16,120*16)
    elif n == 'remote':
        p.setPen(_pen(FG,4)); p.drawArc(QRectF(10,11,44,44), 35*16,110*16); p.drawArc(QRectF(17,18,30,30),35*16,110*16); p.drawArc(QRectF(24,25,16,16),35*16,110*16)
        p.setPen(Qt.NoPen); p.setBrush(GREEN); p.drawEllipse(QRectF(29,45,6,6))
    elif n in ('system','settings'):
        p.setPen(_pen(FG,4)); p.setBrush(Qt.NoBrush); p.drawEllipse(QRectF(20,20,24,24)); p.drawEllipse(QRectF(28,28,8,8))
        for a in range(0,360,45):
            r1,r2=17,24; x1=32+math.cos(math.radians(a))*r1; y1=32+math.sin(math.radians(a))*r1; x2=32+math.cos(math.radians(a))*r2; y2=32+math.sin(math.radians(a))*r2
            p.drawLine(QPointF(x1,y1),QPointF(x2,y2))
    elif n in ('takes','slate'):
        p.setPen(_pen(FG,3.5)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(QRectF(12,23,40,29), 3, 3)
        p.drawLine(QPointF(13,26),QPointF(51,16))
        for x in (18,30,42): p.drawLine(QPointF(x,23),QPointF(x+6,26))
        p.drawLine(QPointF(20,36),QPointF(44,36)); p.drawLine(QPointF(20,43),QPointF(39,43))
    elif n == 'notes':
        p.setPen(_pen(FG,3.5)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(QRectF(17,9,30,46), 3, 3)
        p.drawLine(QPointF(23,22),QPointF(41,22)); p.drawLine(QPointF(23,31),QPointF(41,31)); p.drawLine(QPointF(23,40),QPointF(36,40))
    elif n == 'disk':
        p.setPen(_pen(FG,3.5)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(QRectF(13,17,38,31), 4, 4); p.drawLine(QPointF(17,39),QPointF(47,39))
        p.setPen(Qt.NoPen); p.setBrush(GREEN); p.drawEllipse(QRectF(42,42,5,5))
    elif n == 'idle':
        p.setPen(_pen(MUTED,3.5)); p.setBrush(Qt.NoBrush); p.drawEllipse(QRectF(18,18,28,28)); p.setPen(Qt.NoPen); p.setBrush(GREEN); p.drawEllipse(QRectF(29,29,6,6))
    elif n in ('folder','reveal'):
        p.setPen(_pen(FG,3.5)); p.setBrush(Qt.NoBrush); path=QPainterPath(); path.moveTo(9,23); path.lineTo(24,23); path.lineTo(29,18); path.lineTo(55,18); path.lineTo(57,47); path.lineTo(9,47); path.closeSubpath(); p.drawPath(path)
    elif n == 'open':
        p.setPen(_pen(FG,3.5)); p.drawRoundedRect(QRectF(12,19,31,34),3,3); p.setPen(_pen(BLUE,3.5)); p.drawLine(QPointF(30,34),QPointF(53,11)); p.drawLine(QPointF(38,11),QPointF(53,11)); p.drawLine(QPointF(53,11),QPointF(53,26))
    elif n in ('refresh','reset'):
        p.setPen(_pen(FG,3.5)); p.drawArc(QRectF(13,13,38,38), 35*16,250*16); p.setPen(Qt.NoPen); p.setBrush(FG); p.drawPolygon(_poly([(48,12),(55,21),(43,22)]))
    elif n == 'qr':
        p.setPen(_pen(FG,3)); p.setBrush(Qt.NoBrush)
        for x,y in ((8,8),(39,8),(8,39)):
            p.drawRect(QRectF(x,y,17,17)); p.setBrush(FG); p.drawRect(QRectF(x+5,y+5,7,7)); p.setBrush(Qt.NoBrush)
        p.setPen(Qt.NoPen); p.setBrush(BLUE)
        for x,y in ((35,35),(46,35),(35,46),(49,49),(43,43)): p.drawRect(QRectF(x,y,6,6))
    elif n == 'report':
        p.setPen(_pen(FG,3.5)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(QRectF(17,8,30,48),3,3)
        for y,w in ((21,18),(30,18),(39,14)): p.drawLine(QPointF(23,y),QPointF(23+w,y))
    elif n == 'diagnostics':
        p.setPen(_pen(BLUE,3.5)); p.drawPolyline(_poly([(6,36),(16,36),(21,24),(28,47),(35,17),(42,42),(48,31),(58,31)]))
    elif n == 'browser':
        p.setPen(_pen(FG,3.5)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(QRectF(9,15,46,37),3,3); p.drawLine(QPointF(10,24),QPointF(54,24))
        p.setPen(Qt.NoPen); p.setBrush(RED); p.drawEllipse(QRectF(14,18,4,4)); p.setBrush(YELLOW); p.drawEllipse(QRectF(21,18,4,4)); p.setBrush(GREEN); p.drawEllipse(QRectF(28,18,4,4))
    elif n == 'help':
        p.setPen(_pen(FG,3.5)); p.setBrush(Qt.NoBrush); p.drawEllipse(QRectF(13,13,38,38)); f=QFont(); f.setBold(True); f.setPixelSize(28); p.setFont(f); p.drawText(QRectF(13,11,38,40),Qt.AlignCenter,'?')
    elif n == 'dropdown':
        p.setPen(_pen(FG,4)); p.drawLine(QPointF(20,26),QPointF(32,38)); p.drawLine(QPointF(32,38),QPointF(44,26))
    elif n in ('plus','add'):
        p.setPen(_pen(BLUE,4.5)); p.drawLine(QPointF(32,14),QPointF(32,50)); p.drawLine(QPointF(14,32),QPointF(50,32))
    elif n == 'more':
        p.setPen(Qt.NoPen); p.setBrush(FG)
        for y in (18,32,46): p.drawEllipse(QRectF(28,y-4,8,8))
    elif n == 'edit':
        p.setPen(_pen(FG,3.5)); p.drawRoundedRect(QRectF(12,12,40,40),4,4)
        p.setPen(_pen(BLUE,4)); p.drawLine(QPointF(23,42),QPointF(45,20)); p.drawLine(QPointF(20,45),QPointF(27,43))
    else:
        p.setPen(_pen(BLUE,4)); p.drawEllipse(QRectF(20,20,24,24))

    p.end()
    return pm


def make_icon(name: str, size: int = 64) -> QIcon:
    return QIcon(icon_pixmap(name, size))


def brand_pixmap(size: int = 128) -> QPixmap:
    pm, p, _ = _canvas(size)
    # Keep the brand mark compact and legible at 16-32 px: no fine border.
    p.setPen(_pen(BLUE2, 4.5))
    xs=[14,22,30,38,46,54]; hs=[20,34,50,40,28,16]
    for x,h in zip(xs,hs): p.drawLine(QPointF(x,32-h/2),QPointF(x,32+h/2))
    p.end()
    return pm


def brand_icon(size: int = 128) -> QIcon:
    return QIcon(brand_pixmap(size))
