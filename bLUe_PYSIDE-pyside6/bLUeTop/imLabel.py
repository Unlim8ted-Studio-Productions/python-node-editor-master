"""
This File is part of bLUe software.

Copyright (C) 2017  Bernard Virot <bernard.virot@libertysurf.fr>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
Lesser General Lesser Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
from os.path import dirname, basename
from time import time_ns
from threading import Lock

from PySide6.QtCore import QRect, QRectF, Qt, QPointF, QEvent, QPoint
from PySide6.QtGui import QPainter, QColor, QBrush, QContextMenuEvent, QFont, QPainterPath, \
    QPixmap, QMouseEvent, QPointingDevice, QCursor
from PySide6.QtWidgets import QLabel

from bLUeGui.dialog import dlgWarn
from bLUeTop.drawing import bLUeFloodFill, brushFamily
from bLUeTop.settings import MAX_ZOOM
from bLUeTop.utils import checkeredImage, virtualCursor
from bLUeTop.versatileImg import vImage
from bLUeTop.tablet import bTablet


class imageLabel(QLabel):
    """
    Base class for interactive image displaying
    """
    qp = QPainter()
    qp.setRenderHint(QPainter.Antialiasing)  # may be not very useful ?
    qp.font = QFont("Arial", 8)
    qp.markPath = QPainterPath()
    qp.markRect = QRect(0, 0, 50, 20)
    qp.markPath.addRoundedRect(qp.markRect, 5, 5)

    checkerBrush = QBrush(checkeredImage())

    def __init__(self, mainForm=None, splitWin=None, enterAndLeave=False, parent=None):
        super().__init__(parent=parent)
        self.window = mainForm
        self.splitWin = splitWin
        self.enterAndLeave = enterAndLeave  # if False the widget does not handle enter and leave events
        # global state variables used in mouseEvent.
        self.pressed = False
        self.clicked = True
        self.leaved = True
        self.State = {'ix': 0, 'iy': 0, 'ix_begin': 0, 'iy_begin': 0, 'cloning': ''}
        self.img = None
        # Virtual cursor for brush outline.
        # If set, it is drawn by paintEvent at current brush position,
        # using current brush size.
        # It gives more accurate outlines than QCursor shapes.
        self.virtualCursor = virtualCursor()

    def brushUpdate(self, *args, color=None):
        """
        Sync the current brush/eraser with self.State
        and update the current brush sample.
        *args prevents wrong assignment of signal parameters
        to color when the method is used as a signal slot.

        :param args: unused
        :type args:
        :param color:
        :type color: QColor
        """
        bSpacing, bJitter, bOrientation = 1.0, 0.0, 0
        current = self.State.get('brush', None)
        if current is not None:
            bSpacing = current['spacing']
            bJitter = current['jitter']
            bOrientation = current['orientation']
        s = self.sender()
        if s is not None:
            name = s.objectName()
            if name == 'spacingSlider':
                bSpacing = s.value() / 10
            elif name == 'jitterSlider':
                bJitter = s.value() / 10
            elif name == 'orientationSlider':
                bOrientation = s.value() - 180
        window = self.window
        bSize = window.verticalSlider1.value()
        bOpacity = window.verticalSlider2.value() / 100
        bHardness = window.verticalSlider3.value() / 100
        bFlow = window.verticalSlider4.value() / 100
        if color is not None:
            bColor = color
        elif getattr(window, 'colorChooser', None):
            bColor = window.colorChooser.currentColor()  # selectedColor() cannot be set
        else:
            bColor = Qt.black
        if window.btnValues['eraserButton']:
            self.State['brush'] = window.brushes[-1].getBrush(bSize, bOpacity, bColor, bHardness, bFlow)
        else:
            pattern = window.patternCombo.currentData()
            self.State['brush'] = window.brushCombo.currentData().getBrush(bSize, bOpacity, bColor, bHardness, bFlow,
                                                                           spacing=bSpacing, jitter=bJitter,
                                                                           orientation=bOrientation, pattern=pattern)
        # record current brush into layer brushDict
        if self.img is not None:
            layer = self.img.getActiveLayer()
            if layer.isDrawLayer():
                layer.brushDict = self.State['brush'].copy()
                grForm = layer.getGraphicsForm()
                if grForm is not None:
                    grForm.updateSample()

    def paintEvent(self, e):
        """
        Overrides QLabel paintEvent().
        Displays the presentation layer of a vImage object,
        with its current offset and zooming coefficient.

        :param e: paint event
        :type e:
        """
        mimg = self.img
        if mimg is None:
            return
        qp = self.qp
        window = self.window
        qp.begin(self)
        r = mimg.resize_coeff(self)
        # qp.setRenderHint(QPainter.SmoothPixmapTransform) #  decreases  quality
        # fill background
        qp.fillRect(QRect(0, 0, self.width(), self.height()), vImage.defaultBgColor)
        # draw presentation layer.
        # As offsets can be float numbers, we use a QRectF instead of a QRect.
        # r is relative to the full resolution image, so we use mimg width and height
        w, h = mimg.width() * r, mimg.height() * r
        rectF = QRectF(mimg.xOffset, mimg.yOffset, w, h)
        # draw a checker background to view (semi-)transparent images
        qp.fillRect(rectF, imageLabel.checkerBrush)
        px = mimg.prLayer.qPixmap
        if px is not None:
            qp.drawPixmap(rectF, px, px.rect())
        else:
            currentImage = mimg.prLayer.getCurrentImage()
            qp.drawImage(rectF,
                         currentImage,
                         currentImage.rect()
                         )

        # draw selection rectangle and cloning marker of the active layer, if any
        layer = mimg.getActiveLayer()
        mark = layer.marker
        if layer.visible:
            for rect in layer.sRects:
                if rect is not None:
                    qp.setPen(Qt.green)
                    qp.drawRect(rect.left() * r + mimg.xOffset, rect.top() * r + mimg.yOffset, rect.width() * r,
                                rect.height() * r)
            if not (mark is None or layer.sourceFromFile):
                qp.setPen(Qt.white)
                qp.drawEllipse(mark.x() * r + mimg.xOffset, mark.y() * r + mimg.yOffset, 10, 10)
        # draw the cropping marks
        lm, rm, tm, bm = 0, 0, 0, 0
        if mimg.isCropped:
            c = QColor(128, 128, 128, 192)
            lm = window.cropTool.btnDict['left'].margin * r
            rm = window.cropTool.btnDict['right'].margin * r
            tm = window.cropTool.btnDict['top'].margin * r
            bm = window.cropTool.btnDict['bottom'].margin * r
            qp.fillRect(QRectF(mimg.xOffset, mimg.yOffset, lm, h), c)  # left
            qp.fillRect(QRectF(mimg.xOffset + lm, mimg.yOffset, w - lm, tm), c)  # top
            qp.fillRect(QRectF(mimg.xOffset + w - rm, mimg.yOffset + tm, rm, h - tm), c)  # right
            qp.fillRect(QRectF(mimg.xOffset + lm, mimg.yOffset + h - bm, w - lm - rm, bm), c)  # bottom
        # draw rulers
        if mimg.isRuled:
            deltaX, deltaY = (w - lm - rm) // 3, (h - tm - bm) // 3
            qp.drawLine(lm + mimg.xOffset, deltaY + tm + mimg.yOffset, w - rm + mimg.xOffset,
                        deltaY + tm + mimg.yOffset)
            qp.drawLine(lm + mimg.xOffset, 2 * deltaY + tm + mimg.yOffset, w - rm + mimg.xOffset,
                        2 * deltaY + tm + mimg.yOffset)
            qp.drawLine(deltaX + lm + mimg.xOffset, tm + mimg.yOffset, deltaX + lm + mimg.xOffset,
                        h - bm + mimg.yOffset)
            qp.drawLine(2 * deltaX + lm + mimg.xOffset, tm + mimg.yOffset, 2 * deltaX + lm + mimg.xOffset,
                        h - bm + mimg.yOffset)
        # tag before/after views
        name = self.objectName()
        if name == "label_2" or name == "label_3":
            # draw filled rect
            qp.fillPath(qp.markPath, QBrush(Qt.gray))
            # draw text
            qp.setPen(Qt.white)
            qp.setFont(qp.font)
            qp.drawText(qp.markRect, Qt.AlignCenter | Qt.AlignVCenter, "Before" if name == "label_2" else "After")

        if self.virtualCursor.visible:
            s = self.virtualCursor.size
            qp.drawPixmap(QRect(self.virtualCursor.posX - s/2, self.virtualCursor.posY - s/2, s, s), self.virtualCursor.pixmap)

        qp.end()

    def isSynthesised(self, event):
        """
        Returns True if event is synthesised from a tablet event,
        False otherwise.

        :param event:
        :type event: QEvent
        :return:
        :rtype: boolean
        """

        # Synthesised events keep original pointer type.
        return (event.type() in [QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.MouseButtonRelease])\
                and (event.device().pointerType() != QPointingDevice.PointerType.Generic)

    def mousePressEvent(self, event):
        """
        Mouse press event handler.

        :param event: mouse event
        :type event: QMouseEvent
        """
        eventType = event.type()

        State = self.State
        window = self.window

        # no context menu
        if eventType == QContextMenuEvent:
            return

        # get image and active layer
        img = self.img
        if img is None:
            return
        layer = img.getActiveLayer()
        # non modal DlgWarn needed to handle multiple successive tabletPressEvent
        if not layer.visible:
            dlgWarn('Select a visible layer',
                    info='In Layer Stack, toggle the current layer visibility or choose a visible layer',
                    modal=False)
            return
        elif (window.btnValues['drawFG'] or window.btnValues['drawBG']) and not layer.maskIsEnabled:
            dlgWarn('Enable the mask before masking or unmasking',
                    info='In Layer Stack, right-click the current layer and open Mask Style context menu item',
                    modal=False)
            return
        r = img.resize_coeff(self)
        ############################################################
        # get mouse x, y coordinates (relative to widget).
        # The mouse coordinates relative to the (full size) image are
        # (x - img.xOffset) / r, (y - img.yOffset) / r
        #############################################################
        x, y = event.position().x(), event.position().y()
        modifiers = event.modifiers()
        # Mouse hover generates mouse move events,
        # so, we set pressed to select only non hovering events
        self.pressed = True
        if event.button() == Qt.LeftButton:
            # no move yet
            self.clicked = True
        State['ix'], State['iy'] = x, y
        State['ix_begin'], State['iy_begin'] = x, y
        State['x_imagePrecPos'], State['y_imagePrecPos'] = (x - img.xOffset) // r, (y - img.yOffset) // r
        if layer.isDrawLayer():
            layer.history.addItem(layer.sourceImg.copy())
            if window.btnValues['brushButton'] or window.btnValues['bucket']:
                # starting a new stroke : save initial image for atomic stroke painting  and init intermediate layer
                layer.atomicStrokeImg = layer.sourceImg.copy()
                layer.stroke.fill(QColor(0, 0, 0, 0))
        # add current mask to history
        if window.btnValues['drawFG'] or window.btnValues['drawBG']:
            if layer.maskIsEnabled:
                layer.historyListMask.addItem(layer.mask.copy())
        # dragBtn or arrow
        if layer.isCloningLayer():
            if not (window.btnValues['drawFG'] or window.btnValues['drawBG']):
                if modifiers == Qt.ControlModifier | Qt.AltModifier:  # prevent unwanted clicks
                    if layer.cloningState == 'continue':
                        dlgWarn('Layer already cloned', 'To start a new cloning operation, add another cloning layer')
                        return
                    # set source starting point (coordinates are relative to full size image)
                    layer.sourceX, layer.sourceY = (x - img.xOffset) / r, (y - img.yOffset) / r
                    layer.cloningState = 'start'
            elif layer.cloningState == 'start':
                # set the virtual layer translation (relative to full size image)
                layer.xAltOffset, layer.yAltOffset = (x - img.xOffset) / r - layer.sourceX, \
                                                     (y - img.yOffset) / r - layer.sourceY
                layer.cloningState = 'continue'
                layer.updateCloningMask()
                layer.updateSourcePixmap()

    def mouseMoveEvent(self, event):
        """
        Mouse event handler.
        The handler implements mouse and tablet actions on an imImage.
        It handles image positioning, zooming, and
        tool actions.
        NOTE. Mouse and tablet hover generate mouse move events (mouse and tablet tracking are
              enabled in setupGUI()).

        :param event: mouse event
        :type event: QMouseEvent
        """

        eventType = event.type()

        repaintAfter = True  # flag controlling repainting when done

        window = self.window
        State = self.State
        qp = self.qp

        # no context menu
        if eventType == QContextMenuEvent:
            return

        # get image and active layer
        img = self.img
        if img is None:
            return
        layer = img.getActiveLayer()
        r = img.resize_coeff(self)

        ############################################################
        # get mouse x, y coordinates (relative to widget).
        # The mouse coordinates relative to the (full size) image are
        # (x - img.xOffset) / r, (y - img.yOffset) / r
        #############################################################
        x, y = event.position().x(), event.position().y()
        modifiers = event.modifiers()

        # hover event
        if not self.pressed:
            x_img, y_img = (x - img.xOffset) / r, (y - img.yOffset) / r
            # read input and current colors from active layer (coordinates are relative to the full-sized image)
            clr = img.getActivePixel(x_img, y_img, qcolor=True)
            clrC = img.getActivePixel(x_img, y_img, fromInputImg=False, qcolor=True)
            window.infoView.setText(clr, clrC)
            if layer.isCloningLayer():
                if layer.cloningState == 'continue':
                    mx, my = x_img - layer.xAltOffset, y_img - layer.yAltOffset
                elif layer.cloningState == 'start':
                    mx, my = layer.sourceX, layer.sourceY
                else:
                    mx, my = x_img, y_img
                if layer.sourceFromFile:
                    pxmp = layer.getGraphicsForm().sourcePixmap
                    mx, my = mx * pxmp.width() / layer.width(), my * pxmp.height() / layer.height()
                layer.marker = QPointF(mx, my)
                if layer.sourceFromFile:
                    layer.getGraphicsForm().widgetImg.repaint()
            # update cursor
            self.virtualCursor.setPosition(event.position())
            window.label.repaint()
            return

        # click detection: for tablet, (very) small moves are clicks
        self.clicked = self.clicked and abs(State['ix_begin'] - x) + abs(State['iy_begin'] - y) <= 2

        if img.isMouseSelectable:

            # drawing
            if (window.btnValues['brushButton'] or window.btnValues['eraserButton']) and layer.isDrawLayer():
                self.virtualCursor.setPosition(event.position())
                self.updateVirtualCursorSize()
                self.__strokePaint(layer, x, y, r)
                repaintAfter = False  # repainting is controlled by __strokePaint()

            # marquee tool
            elif window.btnValues['rectangle']:
                # rectangle coordinates are relative to full image
                x_img = (min(State['ix_begin'], x) - img.xOffset) // r
                y_img = (min(State['iy_begin'], y) - img.yOffset) // r
                w = abs(State['ix_begin'] - x) // r
                h = abs(State['iy_begin'] - y) // r
                if min(w, h) > 10:
                    if layer.currSRect:
                        layer.currSRect.setRect(x_img, y_img, w, h)
                    else:
                        layer.currSRect = QRect(x_img, y_img, w, h)
                        layer.sRects.append(layer.currSRect)

            # mask
            elif window.btnValues['drawFG'] or window.btnValues['drawBG']:
                if layer.maskIsEnabled:
                    if layer.isCloningLayer:
                        layer.vlChanged = True
                        # layer.setMaskEnabled(color=True)  # set mask to color mask
                    toolOpacity = window.verticalSlider2.value() / 100
                    if modifiers == Qt.NoModifier:
                        if layer.isSegmentLayer():
                            color = vImage.defaultColor_UnMasked_SM if \
                                window.btnValues['drawFG'] else vImage.defaultColor_Masked_SM
                        else:
                            color = vImage.defaultColor_UnMasked if \
                                window.btnValues['drawFG'] else vImage.defaultColor_Masked
                            color.setAlpha(layer.colorMaskOpacity)
                    else:
                        color = vImage.defaultColor_UnMasked_Invalid
                    qp.begin(layer.mask)
                    # get pen width (relative to image)
                    # w_pen = window.verticalSlider1.value() * r * # / r
                    d = self.State['brush']
                    w_pen = d['size'] * d['tabletW']  # * self.img.resize_coeff(self)
                    # mode source: result is source (=pen) pixel color and opacity
                    qp.setCompositionMode(qp.CompositionMode.CompositionMode_Source)
                    tmp_x = (x - img.xOffset) // r
                    tmp_y = (y - img.yOffset) // r
                    qp.setPen(Qt.NoPen)
                    qp.setBrush(QBrush(color))
                    qp.setOpacity(toolOpacity)
                    # paint the brush tips spaced by 0.25 * w_pen
                    # use 1-norm for performance
                    a_x, a_y = tmp_x - State['x_imagePrecPos'], tmp_y - State['y_imagePrecPos']
                    d = abs(a_x) + abs(a_y)
                    x, y = State['x_imagePrecPos'], State['y_imagePrecPos']
                    radius = w_pen / 2
                    if d == 0:
                        qp.drawEllipse(QPointF(x, y),
                                       radius,
                                       radius
                                       )  # center, radius : QPointF mandatory, else bounding rect topleft and size
                    else:
                        step = w_pen * 0.25 / d
                        for i in range(int(1 / step) + 1):
                            qp.drawEllipse(QPointF(x, y),
                                           radius,
                                           radius
                                           )  # center, radius : QPointF mandatory, else bounding rect topleft and size
                            x, y = x + a_x * step, y + a_y * step
                    qp.end()
                    self.virtualCursor.setPosition(event.position())
                    if layer.isCloningLayer():
                        if not layer.sourceFromFile:
                            layer.marker = QPointF(tmp_x - layer.xAltOffset, tmp_y - layer.yAltOffset)
                        else:
                            pxmp = layer.getGraphicsForm().sourcePixmap
                            layer.marker = QPointF((tmp_x - layer.xAltOffset) * pxmp.width() / layer.width(),
                                                   (tmp_y - layer.yAltOffset) * pxmp.height() / layer.height())
                            layer.getGraphicsForm().widgetImg.repaint()
                    State['x_imagePrecPos'], State['y_imagePrecPos'] = tmp_x, tmp_y
                    ############################
                    # update upper stack
                    # should be layer.applyToStack() if any upper layer visible : too slow
                    # layer.applyToStack()
                    layer.updatePixmap()
                    img.prLayer.update()  # =applyNone()
                    #############################
                    window.label.repaint()

            # drag buttton or arrow
            elif window.btnValues['drag'] or window.btnValues['pointer']:
                # drag image
                if modifiers == Qt.NoModifier:
                    img.xOffset += x - State['ix']
                    img.yOffset += y - State['iy']
                    if window.btnValues['Crop_Button']:
                        window.cropTool.setCropTool(img)

                # drag active layer only for drawing layer or crop tool for others
                elif modifiers == Qt.ControlModifier:
                    layer.drag(x, y, State['ix'], State['iy'], self)
                    # layer.xOffset += (x - State['ix'])
                    # layer.yOffset += (y - State['iy'])
                    # layer.updatePixmap()
                    # img.prLayer.update()  # =applyNone()

                # drag cloning virtual layer
                elif modifiers == Qt.ControlModifier | Qt.AltModifier:
                    if layer.isCloningLayer():
                        layer.xAltOffset += (x - State['ix'])
                        layer.yAltOffset += (y - State['iy'])
                        layer.vlChanged = True
                        if layer.maskIsSelected or not layer.maskIsEnabled:
                            layer.setMaskEnabled(color=False)  # set to opacity mask
                        layer.applyCloning(seamless=False, showTranslated=True, moving=True)

        # not mouse selectable widget : probably before window alone !
        else:
            if modifiers == Qt.NoModifier:
                img.xOffset += (x - State['ix'])
                img.yOffset += (y - State['iy'])

        # update current coordinates
        State['ix'], State['iy'] = x, y
        if layer.isGeomLayer():
            layer.tool.moveRotatingTool()

        # updates
        if repaintAfter:
            self.repaint()

        # sync split views
        if self.objectName() == 'label_2':
            self.splitWin.syncSplitView(window.label_3, window.label_2)
            window.label_3.repaint()
        elif self.objectName() == 'label_3':
            self.splitWin.syncSplitView(window.label_2, window.label_3)
            window.label_2.repaint()

    def mouseReleaseEvent(self, event):
        """
        Mouse event handler.
        The handler implements mouse actions on an imImage displayed in a QLabel.
        It handles image positioning, zooming, and
        tool actions.

        :param event: mouse event
        :type event: QMouseEvent
        """

        # Forbid multiple release events after a press event
        if not self.pressed:
            return

        eventType = event.type()

        window = self.window

        # no context menu
        if eventType == QContextMenuEvent:
            return
        # get image and active layer
        img = self.img
        if img is None:
            return
        layer = img.getActiveLayer()
        r = img.resize_coeff(self)

        ############################################################
        # get mouse x, y coordinates (relative to widget).
        # The mouse coordinates relative to the (full size) image are
        # (x - img.xOffset) / r, (y - img.yOffset) / r
        #############################################################
        x, y = event.position().x(), event.position().y()
        modifiers = event.modifiers()
        self.pressed = False
        if event.button() == Qt.LeftButton:
            if layer.maskIsEnabled \
                    and layer.getUpperVisibleStackIndex() != -1 \
                    and (window.btnValues['drawFG'] or window.btnValues['drawBG']):
                layer.applyToStack()
            if img.isMouseSelectable:
                if window.btnValues['rectangle']:
                    layer.currSRect = None  # go to next rectangle
                    layer.sRects = [rect for rect in layer.sRects if rect.isValid()]
                # click event
                if self.clicked:
                    x_img, y_img = (x - img.xOffset) / r, (y - img.yOffset) / r
                    # read input and current colors from active layer
                    # coordinates are relative to the full-sized image
                    clr = img.getActivePixel(x_img, y_img, qcolor=True)
                    clrC = img.getActivePixel(x_img, y_img, fromInputImg=False, qcolor=True)
                    # red, green, blue = clr.red(), clr.green(), clr.blue()
                    # read color from presentation layer
                    redP, greenP, blueP = img.getPrPixel(x_img, y_img)
                    # color chooser : when visible the colorPicked signal is not emitted
                    if getattr(window, 'colorChooser', None) and window.colorChooser.isVisible():
                        if modifiers == Qt.ControlModifier | Qt.ShiftModifier:
                            window.colorChooser.setCurrentColor(clr)
                        elif modifiers == Qt.ControlModifier | Qt.AltModifier:
                            window.colorChooser.setCurrentColor(clrC)
                        elif modifiers == Qt.ControlModifier:
                            window.colorChooser.setCurrentColor(QColor(redP, greenP, blueP))
                    else:
                        if window.btnValues['rectangle']:
                            # remove rectangle from selection
                            if modifiers == Qt.ControlModifier:
                                for rect in layer.sRects:
                                    if rect.contains(x_img, y_img):
                                        layer.sRects.remove(rect)
                                        layer.selectionChanged.sig.emit()
                                        break
                        else:
                            # emit colorPicked signal
                            layer.colorPicked.sig.emit(x_img, y_img, modifiers)
                        # Flood fill tool
                        if layer.isDrawLayer() and window.btnValues['bucket']:
                            if getattr(window, 'colorChooser', None):
                                bucketColor = window.colorChooser.currentColor()
                            else:
                                bucketColor = Qt.black
                            bLUeFloodFill(layer, int(x_img), int(y_img), bucketColor)
                            layer.applyToStack()

                else:  # not clicked
                    if window.btnValues['rectangle']:
                        layer.selectionChanged.sig.emit()
                    # cloning layer
                    elif layer.isCloningLayer():
                        if layer.vlChanged:
                            # the virtual layer was moved : clone
                            layer.applyCloning(seamless=True, showTranslated=True, moving=True)
                            layer.vlChanged = False

        self.repaint()

        # sync split views
        if self.objectName() == 'label_2':
            self.splitWin.syncSplitView(window.label_3, window.label_2)
            window.label_3.repaint()
        elif self.objectName() == 'label_3':
            self.splitWin.syncSplitView(window.label_2, window.label_3)
            window.label_2.repaint()

    def wheelEvent(self, event):
        """
        Mouse wheel event handler : zooming
        for imImage objects.

        :param event: mouse wheel event
        :type event: QWheelEvent
        """
        window = self.window
        if window.asButton.isChecked():
            return
        img = self.img
        pos = event.position()
        modifiers = event.modifiers()
        delta = event.angleDelta()
        # delta unit is 1/8 of degree.
        # On Windows, Alt modifier may toggle horizontal/vertical  wheels,
        # so we sum up the 2 delta coordinates.
        numSteps = (delta.x() + delta.y()) / 1200.0
        layer = img.getActiveLayer()
        if modifiers == Qt.NoModifier:
            img.Zoom_coeff *= (1.0 + numSteps)
            if layer.isDrawLayer():
                self.updateVirtualCursorSize()
            # max Zoom for previews
            if img.Zoom_coeff > MAX_ZOOM:
                img.Zoom_coeff /= (1.0 + numSteps)
                return
            # correct image offset to keep unchanged the image point
            # under the cursor : (pos - offset) / resize_coeff is invariant
            img.xOffset = -pos.x() * numSteps + (1.0 + numSteps) * img.xOffset
            img.yOffset = -pos.y() * numSteps + (1.0 + numSteps) * img.yOffset
            if window.btnValues['Crop_Button']:
                window.cropTool.setCropTool(img)
            if layer.isGeomLayer():
                # layer.view.widget().tool.moveRotatingTool()
                layer.tool.moveRotatingTool()
        elif modifiers == Qt.ControlModifier:
            # cropTool aware zooming
            # layer.Zoom_coeff *= 1.0 + numSteps  # useless and misleading
            layer.zoom(pos, numSteps, self)
        # cloning layer zoom
        elif layer.isCloningLayer() and modifiers == Qt.ControlModifier | Qt.AltModifier:
            layer.AltZoom_coeff *= (1.0 + numSteps)
            layer.applyCloning(seamless=True, showTranslated=True, moving=True)

        self.repaint()

        # sync split views
        if self.objectName() == 'label_2':
            self.splitWin.syncSplitView(window.label_3, window.label_2)
            window.label_3.repaint()
        elif self.objectName() == 'label_3':
            self.splitWin.syncSplitView(window.label_2, window.label_3)
            window.label_2.repaint()

    def tabletEvent(self, event):
        """

        Only imageLabel instances may handle tablet events.
        The image editor in plain (i.e. != before/after) mode accepts and handles them.
        Other imageLabel instances ignore them.
        All other widget classes do not handle them. For these last classes tablet events
        are transformed into synthesised mouse events and handled as such.

        :param event:
        :type event: QTabletEvent
        """
        if self.objectName() == 'label':
            event.accept()
        else:
            event.ignore()
            return

        d = self.State['brush']
        eventType = event.type()

        if eventType == QEvent.TabletMove:
            # Event pressure range is [0, 1]
            # xTilt and yTilt are from pen to the perpendicular to tablet in range [-60, 60] degrees.
            # Positive values are towards the tablet's physical bottom-right.
            # d['tabletW'] is used as a  multiplicative coefficient for brush size.
            # It should be > 0 and may be > 1
            v = bTablet.getWidthValuator()
            if v == bTablet.valuator.PressureValuator:
                d['tabletW'] = 0.2 + event.pressure()
            elif bTablet.valuator.HTiltValuator:
                hValue = ((event.xTilt() + 60.0) / 120.0)
                d['tabletW'] = 0.2 + hValue
            elif bTablet.valuator.VTiltValuator:
                vValue = ((event.yTilt() + 60.0) / 120.0)
                d['tabletW'] = 0.2 + vValue
            elif v == bTablet.valuator.TiltValuator:
                vValue = ((event.yTilt() + 60.0) / 120.0)
                hValue = ((event.xTilt() + 60.0) / 120.0)
                d['tabletW'] = 0.2 + max(hValue, vValue)
            else:
                d['tabletW'] = 1.0

            v = bTablet.getAlphaValuator()
            # d['tabletA'] is used as a multiplicative coefficient for brush opacity.
            # It should be > 0 and can be > 1 : resulting brush opacity is clipped to 1.0.
            if v == bTablet.valuator.VTiltValuator:
                d['tabletA'] = 1.0 + event.yTilt() / 60.0
            elif v == bTablet.valuator.HTiltValuator:
                d['tabletA'] = 1.0 + event.xTilt() / 60.0
            elif v == bTablet.valuator.TiltValuator:
                d['tabletA'] = 1.0 + max(event.xTilt() / 60.0, event.yTilt() / 60.0)
            elif v == bTablet.valuator.PressureValuator:
                d['tabletA'] = event.pressure()
            else:
                d['tabletA'] = 1.0

            v = bTablet.getSatValuator()
            # d['tabletS'] is used as a multiplicative coefficent for the saturation of brush pixel colors.
            # It should be > 0 and can be > 1 : resulting saturations are clipped to 1.0.
            if v == bTablet.valuator.VTiltValuator:
                d['tabletS'] = 1.0 + event.yTilt() / 60.0
            elif v == bTablet.valuator.HTiltValuator:
                d['tabletS'] = 1.0 + event.xTilt() / 60.0
            elif v == bTablet.valuator.TiltValuator:
                d['tabletS'] = 1.0 + max(event.xTilt() / 60.0, event.yTilt() / 60.0)
            elif v == bTablet.valuator.PressureValuator:
                d['tabletS'] = event.pressure() + 0.5
            else:
                d['tabletS'] = 1.0

            # draw move
            self.mouseMoveEvent(event)

            # restore brush
            d['tabletW'] = 1.0
            d['tabletA'] = 1.0
            d['tabletS'] = 1.0

        elif eventType == QEvent.TabletPress:
            self.mousePressEvent(event)

        elif eventType == QEvent.TabletRelease:
            self.mouseReleaseEvent(event)

        else:
            print('unhandled tablet event', eventType)

    def updateCursor(self, event):
        """
        Sync system and virtual cursors with the states of tool buttons.

        :param event:
        :type event: QEvent
        """
        window = self.window
        # set tool cursor
        layer = window.label.img.getActiveLayer()

        # sync tool buttons with tablet pen/eraser button.
        if event.pointerType() == QPointingDevice.PointerType.Eraser:
            self.setCursor(window.cursors['Eraser'])
            if self.window.btnValues['brushButton']:
                self.window.btns['eraserButton'].setChecked(True)  # tool buttons are mutually exclusive
            elif self.window.btnValues['drawBG']:
                self.window.btns['drawFG'].setChecked(True)  # unmasking (erasing mask)
        elif event.pointerType() == QPointingDevice.PointerType.Pen:
            self.setCursor(QCursor(Qt.ArrowCursor))
            if self.window.btnValues['eraserButton']:
                self.window.btns['brushButton'].setChecked(True)
            elif self.window.btnValues['drawFG']:  # drawFG = unmasking
                self.window.btns['drawBG'].setChecked(True)
        #else:
            # unhandled stylus
            #self.setCursor(QCursor(Qt.ArrowCursor))

        # sync cursor and virtual cursor with tool buttons
        if window.btnValues['drawFG'] or window.btnValues['drawBG']:
            self.virtualCursor.pixmap = window.cursors['Circle_Pixmap']
            self.updateVirtualCursorSize()
            self.virtualCursor.visible = True

        elif window.btnValues['brushButton'] or window.btnValues['eraserButton']:
            if layer.isDrawLayer():
                self.virtualCursor.pixmap = self.State['brush']['cursor']
                self.updateVirtualCursorSize()
                self.virtualCursor.visible = True

        elif window.btnValues['bucket']:
            if layer.isDrawLayer():
                self.setCursor(window.cursors['Bucket'])
                self.virtualCursor.visible = False

        elif window.btnValues['drag']:
            self.setCursor(QCursor(Qt.OpenHandCursor))
            self.virtualCursor.visible = False

        elif window.btnValues['colorPicker']:
            if layer.isAdjustLayer():
                if layer.view.isVisible():
                    self.setCursor(window.cursors['EyeDropper'])
                    self.virtualCursor.visible = False
        #else:
            #self.setCursor(Qt.ArrowCursor)

        # When hovering, a tablet may not send enter and leave events.
        # As a workaround, we try to erase the virtual cursor when it is "about" to leave.
        if event.position().x() <= 0 or event.position().y() <= 0:
            self.virtualCursor.visible = False

    def updateVirtualCursorSize(self):
        """
        Updates
        """

        d = self.State['brush']
        self.virtualCursor.size = max(d['size'] * self.img.resize_coeff(self) * d['tabletW'], 10)

    def enterEvent(self, event):
        """
        Mouse enter event handler.
        The method syncs current cursors
        with tool buttons
        :param event:
        :type event: Qevent
        """
        if not self.enterAndLeave:
            return
        self.updateCursor(event)

    def leaveEvent(self, event):
        """
        Mouse leave event handler.
        :param event:
        :type event: QEvent
        """
        if not self.enterAndLeave:
            return
        self.unsetCursor()  # back to parent cursor
        if self.virtualCursor.visible:
            self.virtualCursor.visible = False
            self.window.label.update()  # cleaning virtual cursor

    def __strokePaint(self, layer, x, y, r):
        """
        Private drawing function. Should be called only by the mouse event handler.
        THe method paints a whole stroke (i.e., a drawing without any release of mouse button)
        over layer.sourceImg

        :param layer: drawing layer
        :type layer: QDrawingLayer
        :param x: mouse x coord.
        :type x: int
        :param y: mouse y coord.
        :type y: int
        :param r: image resizing coeff.
        :type r: float
        """

        def updateLayer(sender=''):

            # Should be layer.applyToStack() if any upper layer visible : too slow !
            # We only update the current drawing layer. Higher drawing layers do not need any updating : they
            # transparently transmit modifications (see QDrawingLayer.inputImg()).
            # All higher non-drawing layers should be not visible.
            # To handle high-frequency events, we maintain the refresh rate under 5 per second.
            # Large (and fast) moves may be displayed anyway.
            # Due to the timer, mutual exclusion is needed.

            mutex.acquire()
            t = time_ns() - layer.last_refresh

            if t >= 2 * (10**8): #  or layer.uRect.width() + layer.uRect.height() > 500:
                if layer.uRect.isValid():
                    layer.execute(l=layer, bRect=layer.uRect)
                    img.prLayer.update(bRect=layer.uRect)
                    layer.uRect = QRect()
                    layer.last_refresh = time_ns()
                    if sender != 'timer':
                        """
                        # useless if Qt.UniqueConnection works as expected
                        try:
                            layer.timer.timeout.disconnect()  
                        except RuntimeError:
                            pass
                        """
                        layer.timer.timeout.connect(lambda: updateLayer(sender='timer'), Qt.UniqueConnection)
                        layer.timer.start(300)  # should be greater than refresh rate to minimize timer triggering
                self.repaint()
            mutex.release()

        mutex = Lock()
        img = self.img
        State = self.State
        qp = self.qp
        # get image coordinates
        x_img = (x - img.xOffset) // r
        y_img = (y - img.yOffset) // r

        # draw the stroke to intermediate layer
        if self.window.btnValues['brushButton']:
            qp.begin(layer.stroke)
            qp.setCompositionMode(qp.CompositionMode.CompositionMode_SourceOver)
            State['x_imagePrecPos'], State['y_imagePrecPos'], modRect = brushFamily.brushStrokeSeg(qp,
                                                                                          State['x_imagePrecPos'],
                                                                                          State['y_imagePrecPos'],
                                                                                          x_img, y_img,
                                                                                          State['brush']
                                                                                                  )
            qp.end()

            rectI = QRect(0, 0, img.width() - 1, img.height() - 1)
            modRect = modRect.toRect()
            modRect = modRect.intersected(rectI)

            if modRect.isEmpty():
                updateLayer()
                return

            # draw texture aligned with image
            strokeTex = layer.stroke.copy(modRect)
            p = State['brush']['pattern']
            if p is not None:
                if p.pxmp is not None:
                    h, v = modRect.left() % p.pxmp.width(),  modRect.top() % p.pxmp.height()
                    modRect.setTopLeft(modRect.topLeft() - QPoint(h, v))
                    strokeTex = layer.stroke.copy(modRect)
                    qp1 = QPainter(strokeTex)
                    qp1.setCompositionMode(qp.CompositionMode.CompositionMode_DestinationIn)
                    qp1.setBrush(QBrush(p.pxmp))
                    qp1.fillRect(QRect(0, 0, strokeTex.width(), strokeTex.height()), QBrush(p.pxmp))
                    qp1.end()
                    # restore modRect and cut strokeTex accordingly
                    modRect.setTopLeft(modRect.topLeft() + QPoint(h, v))
                    strokeTex = strokeTex.copy(QRect(h, v, modRect.width(), modRect.height()))
            # restore source image and paint
            # the whole stroke with current brush opacity.
            # Restoring source image enables iterative calls showing
            # stroke progress
            qp.begin(layer.sourceImg)
            qp.setCompositionMode(qp.CompositionMode.CompositionMode_Source)
            qp.drawImage(modRect, layer.atomicStrokeImg, modRect)
            qp.setOpacity(min(State['brush']['opacity'] * State['brush']['tabletA'], 1.0))
            qp.setCompositionMode(qp.CompositionMode.CompositionMode_SourceOver)
            qp.drawImage(modRect, strokeTex)
            qp.end()
        elif self.window.btnValues['eraserButton']:
            qp.begin(layer.sourceImg)
            qp.setCompositionMode(qp.CompositionMode.CompositionMode_DestinationIn)
            State['x_imagePrecPos'], State['y_imagePrecPos'], modRect = brushFamily.brushStrokeSeg(qp,
                                                                                          State['x_imagePrecPos'],
                                                                                          State['y_imagePrecPos'],
                                                                                          x_img, y_img,
                                                                                          State['brush']
                                                                                                   )
            qp.end()
            modRect = modRect.toRect()
            if modRect.isEmpty():
                updateLayer()
                return

        layer.uRect = layer.uRect.united(modRect)
        updateLayer()


class slideshowLabel(imageLabel):
    """
    This class should be used to display cross-faded
    transitions between images.
    """

    def __init__(self,  mainForm=None, splitWin=None, enterAndLeave=False, parent=None):
        super().__init__(mainForm=mainForm, splitWin=splitWin, enterAndLeave=enterAndLeave, parent=parent)
        self.img = None
        self.prevImg = None
        self.prevOpacity = 0.0

    def paintEvent(self, e):
        """
        Overrides imageLabel paintEvent().

        :param e: paint event
        :type e:
        """
        mimg = self.img
        if mimg is None:
            return

        r = mimg.resize_coeff(self)
        qp = self.qp
        # painting directly on the slideshowLabel slows down operations, especially when using a X server.
        # So, paint operations are done on a intermediate pixmap and exposed by calling the base paintEvent.
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.transparent)

        qp.begin(pixmap)
        # smooth painting
        # qp.setRenderHint(QPainter.SmoothPixmapTransform)
        # fill background
        qp.fillRect(QRect(0, 0, self.width(), self.height()), vImage.defaultBgColor)
        # draw presentation layer.
        # As offsets can be float numbers, we use a QRectF instead of a QRect.
        # r is relative to the full resolution image, so we use mimg width and height
        w, h = mimg.width() * r, mimg.height() * r
        rectF = QRectF(mimg.xOffset, mimg.yOffset, w, h)
        # draw a checker background to view (semi-)transparent images
        qp.fillRect(rectF, imageLabel.checkerBrush)

        px = mimg.prLayer.qPixmap
        if px is not None:
            qp.drawPixmap(rectF, px, px.rect())
        else:
            currentImage = mimg.prLayer.getCurrentImage()
            qp.drawImage(rectF,
                         currentImage,
                         currentImage.rect()
                         )
        qp.drawText(rectF.right(), rectF.bottom(), basename(dirname(mimg.filename)))  # likely the name of album

        mimg = self.prevImg
        if mimg is None:
            qp.end()
            self.setPixmap(pixmap)
            QLabel.paintEvent(self, e)
            return
        r = mimg.resize_coeff(self)
        w, h = mimg.width() * r, mimg.height() * r
        rectF = QRectF(mimg.xOffset, mimg.yOffset, w, h)
        px = mimg.prLayer.qPixmap
        if px is not None:
            qp.setOpacity(self.prevOpacity)
            qp.drawPixmap(rectF, px, px.rect())
        qp.end()
        self.setPixmap(pixmap)
        QLabel.paintEvent(self, e)
