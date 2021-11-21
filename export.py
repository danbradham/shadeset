import re
from string import Template
from textwrap import dedent

from Qt import QtCore, QtGui, QtSvg, QtWidgets


UI_SCALE = None
STYLES = {
    # Colors
    'dark': '#3A3A3A',
    'dark_overlay': '#BB3A3A3A',
    'mid': '#404040',
    'mid_overlay': '#BB404040',
    'light': '#BBBBBB',
    'light_overlay': '#BBBBBBBB',
    'red': '#C45A5A',
    'green': '#6CBA82',
    'blue': '#608AC9',
    'blue_overlay': '#BB608AC9',
    'purple': '#945CDA',
    'transparent': '#00000000',

    # Snip Colors
    'snip_background': '#22608AC9',
    'snip_foreground': '#01608AC9',
    'snip_empty': '#00000000',

    # Presets
    'border_rounded': 'border-radius: 8px',
    'border_dashed': 'border: 2px dashed',
}
ICONS = {
    'cross': 'shadeset/ui/res/cross.png',
    'check': 'shadeset/ui/res/check.png',
    'check_anim': 'shadeset/ui/res/check_anim.svg',
    'error': 'shadeset/ui/res/error.png',
    'error_anim': 'shadeset/ui/res/error_anim.svg',
    'drop': 'shadeset/ui/res/dragdrop.png',
    'snip': 'shadeset/ui/res/snip.png',
    'browse': 'shadeset/ui/res/browse.png',
}
IMG_EXTS = [
    ext.data().decode()
    for ext in QtGui.QImageReader.supportedImageFormats()
]
STYLE_CACHE = {}


def get_screen_dpi():
    '''Get screen DPI to scale UI independent of monitor size.'''

    app = QtWidgets.QApplication.instance()
    if app:
        return float(app.desktop().logicalDpiX())
    return 96.0


def get_ui_scale():
    '''Get UI scale factor'''

    global UI_SCALE

    if UI_SCALE is None:
        UI_SCALE = get_screen_dpi() / 96.0

    return UI_SCALE


def px(value):
    '''Scale a pixel value based on screen dpi.'''

    return int(get_ui_scale() * value)


def animate(obj, prop, duration, curve, start_value, end_value):
    '''Wraps QPropertyAnimation so we can pass all required values as kwargs'''

    anim = QtCore.QPropertyAnimation(obj, prop.encode())
    anim.setDuration(duration)
    anim.setEasingCurve(curve)
    anim.setStartValue(start_value)
    anim.setEndValue(end_value)
    return anim


def fade_in(obj, **kwargs):

    kwargs.setdefault('prop', 'opacity')
    kwargs.setdefault('duration', 150)
    kwargs.setdefault('curve', QtCore.QEasingCurve.OutQuad)
    kwargs.setdefault('start_value', 0)
    kwargs.setdefault('end_value', 1)

    obj.fx = QtWidgets.QGraphicsOpacityEffect(obj)
    obj.setGraphicsEffect(obj.fx)
    return animate(obj.fx, **kwargs)


def parallel_group(obj, *anims):
    '''Returns a QtCore.QParallelAnimationGroup with anims added...
    :param obj: Parent widget of animation group
    :param *anims: QtCore.QPropertyAnimation instances
    .. usage::
        group = parallel_group(
            slide(
                widget_a,
                start_value=QtCore.QPointF(0, 0),
                end_value=QtCore.QPointF(100, 100),
            ),
            fade_in(widget_b),
            fade_in(widget_c),
        )
        group.start()
    '''

    group = QtCore.QParallelAnimationGroup(obj)
    for anim in anims:
        group.addAnimation(anim)
    return group


def format_style(cls, style):
    '''Formats a stylesheet.

    1. Dedent.
    2. Replace variables.
    3. Scale pixel values making them dpi aware.
    '''

    if cls not in STYLE_CACHE:
        style = dedent(style)
        style = Template(style).substitute(**STYLES)
        style = Template(style).substitute(**STYLES)  # Handle nested vars

        def scale_px(match):
            value = px(int(match.group(1)))
            return f'{value}px'

        STYLE_CACHE[cls] = re.sub(r'(\d+)px', scale_px, style)

    return STYLE_CACHE[cls]


def FadeIn(cls):
    '''Fade in this widget whenever it is shown.'''

    def show(self, *args, **kwargs):
        if self.isHidden():
            self._anim = fade_in(self)
            self._anim.start()
        super(cls, self).show(*args, **kwargs)

    cls.show = show

    return cls


def StyledWidget(cls):
    '''Convenience method to set a QWidgets stylesheet from it's style class
    attributes.
    '''

    cls__init__ = cls.__init__

    def __init__(self, *args, **kwargs):
        cls__init__(self, *args, **kwargs)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        if hasattr(cls, 'css'):
            self.setStyleSheet(format_style(cls, cls.css))

    def setStyledProperty(self, prop, value):
        self.setProperty(prop, value)
        self.style().unpolish(self)
        self.style().polish(self)

    cls.__init__ = __init__
    cls.setStyledProperty = setStyledProperty

    return cls


def get_image_paths_from_mime_data(mimeData):
    '''Get all paths to local images contained in the mimeData.'''

    files = [url.toLocalFile() for url in mimeData.urls() if url.toLocalFile()]
    return [file for file in files if file.rsplit('.')[-1] in IMG_EXTS]


@StyledWidget
class Snip(QtWidgets.QDialog):
    '''Screen snipping dialog used to grab a section of your desktop.

    Arguments:
        region (QtCore.QRect)- Optional starting region
        parent (QWidget) - Parent QWidget
    '''

    def __init__(self, region=None, proportion=None, parent=None):
        super(Snip, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Get screen geometry
        app = QtWidgets.QApplication.instance()
        desktop_region = app.primaryScreen().virtualGeometry()
        self.setGeometry(desktop_region)

        cursor_pixmap = QtGui.QPixmap(ICONS['cross']).scaled(
            QtCore.QSize(px(32), px(32)),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.FastTransformation,
        )
        self.setCursor(QtGui.QCursor(cursor_pixmap, px(15), px(15)))

        self.region = region or QtCore.QRect()
        self.proportion = proportion
        self._selection = False
        self._selecting = False
        self._moving = False
        self._origin = None
        self._last_pos = None

    def select(self, region):
        self.region = region
        self._selection = True
        self.update()

    def capture(self, region):
        '''Grab the current virtual desktop.'''

        app = QtWidgets.QApplication.instance()
        pixmap = app.primaryScreen().grabWindow(
            app.desktop().winId(),
            region.x(),
            region.y(),
            region.width(),
            region.height()
        )
        return pixmap

    @classmethod
    def select_and_capture(cls, region=None, proportion=None):
        snip = cls(region=None, proportion=proportion)
        if snip.exec_():
            return snip.capture(snip.global_region)

    @property
    def global_region(self):
        rect = QtCore.QRect(self.region)
        rect.moveTopLeft(self.mapToGlobal(self.region.topLeft()))
        return rect

    def mousePressEvent(self, event):
        self._origin = event.pos()
        if event.button() == QtCore.Qt.LeftButton:
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._selection = True
            if self._moving:
                dx = self._last_pos - event.pos()
                self._origin = self.region.topLeft() - dx
                self.region.moveTopLeft(self._origin)
            else:
                self.region = QtCore.QRect(
                    self._origin,
                    event.pos(),
                ).normalized()
                if self.proportion:
                    height_ratio = 1.0 / self.proportion
                    self.region.setHeight(self.region.width() * height_ratio)

            self.update()

        self._last_pos = event.pos()

    def mouseReleaseEvent(self, event):
        self._origin = None
        self._selecting = False
        self._selection = True
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()
            return

        if event.key() == QtCore.Qt.Key_Space:
            self._moving = True

        if self._selecting:
            cursor_pos = QtGui.QCursor.pos()
            dx = None
            if event.key() == QtCore.Qt.Key_Left:
                dx = QtCore.QPoint(-1, 0)
            if event.key() == QtCore.Qt.Key_Up:
                dx = QtCore.QPoint(0, -1)
            if event.key() == QtCore.Qt.Key_Right:
                dx = QtCore.QPoint(1, 0)
            if event.key() == QtCore.Qt.Key_Down:
                dx = QtCore.QPoint(0, 1)

            if dx:
                self._origin = self._origin + dx
                QtGui.QCursor.setPos(cursor_pos + dx)

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            self._moving = False

    def focusOutEvent(self, event):
        self.close()
        event.accept()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(painter.Antialiasing)

        # Paint background
        painter.fillRect(
            self.rect(),
            QtGui.QColor(STYLES['snip_background']),
        )
        if self._selection:
            painter.setCompositionMode(painter.CompositionMode_Clear)
            painter.fillRect(
                self.region,
                QtGui.QColor(STYLES['snip_empty']),
            )
            painter.setCompositionMode(painter.CompositionMode_SourceOver)
            painter.fillRect(
                self.region,
                QtGui.QColor(STYLES['snip_foreground']),
            )
            pen = QtGui.QPen()
            pen.setBrush(QtGui.QColor(STYLES['light']))
            pen.setWidth(px(2))
            pen.setStyle(QtCore.Qt.DashLine)
            pen.setJoinStyle(QtCore.Qt.RoundJoin)
            pen.setDashPattern((px(2), px(2)))
            painter.setPen(pen)
            painter.drawRect(self.region)
        else:
            pen = QtGui.QPen()
            pen.setBrush(QtGui.QColor(STYLES['light']))
            painter.setPen(pen)
            font = painter.font()
            font.setPixelSize(px(18))
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                QtCore.Qt.AlignCenter,
                'Click and Drag'
            )


def select_and_capture(region=None, proportion=None, before=None, after=None):
    '''Select and return a region of your screen as a pixmap.'''

    try:
        if before:
            before()
        return Snip.select_and_capture(region, proportion)
    finally:
        if after:
            after()


@FadeIn
@StyledWidget
class ImageDropValidator(QtWidgets.QWidget):

    css = '''
    QWidget {
        background: $dark_overlay;
    }
    QWidget[valid=true] {
        $border_rounded;
        $border_dashed $green;
    }
    QWidget[valid=false] {
        $border_rounded;
        $border_dashed $red;
    }
    #clear {
        background: $transparent;
        border: 0;
        border-radius: 0;
    }
    '''

    def __init__(self, parent=None):
        super(ImageDropValidator, self).__init__(parent=parent)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )

        self.icon = QtSvg.QSvgWidget(parent=self)
        self.icon.setObjectName('clear')
        self.icon.setFixedSize(96, 96)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.icon)
        self.setLayout(layout)

    def update_icon(self, is_valid):
        self.icon.load((ICONS['error_anim'], ICONS['check_anim'])[is_valid])

    def validate(self, mimeData):
        images = get_image_paths_from_mime_data(mimeData)
        is_valid = bool(images and len(images) == 1)
        self.setStyledProperty('valid', is_valid)
        self.update_icon(is_valid)
        return is_valid


@StyledWidget
class Image(QtWidgets.QLabel):

    css = '''
    background: $transparent;
    '''
    scale_args = (
        QtCore.Qt.KeepAspectRatio,
        QtCore.Qt.SmoothTransformation,
    )

    def __init__(self, image=None, parent=None):
        super(Image, self).__init__(parent=None)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(1, 1)

        self.state = {
            'pixmap': None,
            'pixmap_opacity': None,
            'animation': None,
            'next_pixmap': None,
            'next_rect': QtCore.QRect(),
        }
        if image:
            self.setImage(image)

    @QtCore.Property(QtCore.QRect)
    def next_rect(self):
        return self.state['next_rect']

    @next_rect.setter
    def next_rect(self, value):
        self.state['next_rect'] = value
        self.update()

    @QtCore.Property(float)
    def pixmap_opacity(self):
        return self.state['pixmap_opacity']

    @pixmap_opacity.setter
    def pixmap_opacity(self, value):
        self.state['pixmap_opacity'] = value
        self.update()

    def finish_animation(self):
        self.state['pixmap'] = self.state['next_pixmap']
        self.state['pixmap_opacity'] = 1.0
        self.state['animation'] = None
        self.state['next_pixmap'] = None
        self.update()

    def setImage(self, image, transition=False):
        if not transition:
            self.state['pixmap'] = QtGui.QPixmap(image)
            self.update()
        else:
            self.state['next_pixmap'] = QtGui.QPixmap(image)

            origin = self.mapFromGlobal(QtGui.QCursor.pos())
            if not self.rect().contains(origin):
                origin = self.rect().center()

            # Animate image transition
            animation = parallel_group(
                self,
                animate(
                    self,
                    prop='next_rect',
                    duration=200,
                    curve=QtCore.QEasingCurve.OutQuad,
                    start_value=QtCore.QRect(origin, QtCore.QSize(0, 0)),
                    end_value=self.rect(),
                ),
                animate(
                    self,
                    prop='pixmap_opacity',
                    duration=150,
                    curve=QtCore.QEasingCurve.OutQuad,
                    start_value=1.0,
                    end_value=0.0,
                )
            )
            animation.finished.connect(self.finish_animation)
            animation.start()
            self.state['animation'] = animation

    def paintPixmap(self, rect, pixmap, opacity, painter):
        image = QtGui.QImage(
            self.rect().size(),
            QtGui.QImage.Format_ARGB32,
        )
        image.fill(QtCore.Qt.transparent)
        painter.begin(image)
        painter.setRenderHint(painter.Antialiasing)
        painter.setOpacity(opacity)
        painter.drawPixmap(rect, pixmap)
        painter.end()

        painter.begin(self)
        painter.setRenderHint(painter.Antialiasing)
        painter.setBrush(QtGui.QPixmap(image))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), px(8), px(8))
        painter.end()

    def paintEvent(self, event):
        painter = QtGui.QPainter()

        if self.state['pixmap']:
            pixmap = self.state['pixmap'].scaled(
                self.rect().size(),
                self.scale_args[0],
                self.scale_args[1],
            )

            if self.scale_args[0] == QtCore.Qt.KeepAspectRatio:
                rect = pixmap.rect()
                rect.moveCenter(self.rect().center())
            else:
                crop_rect = self.rect()
                crop_rect.moveCenter(pixmap.rect().center())
                pixmap = pixmap.copy(crop_rect)
                rect = self.rect()

            opacity = self.state['pixmap_opacity']
            self.paintPixmap(rect, pixmap, opacity, painter)

        if self.state['next_pixmap']:
            pixmap = self.state['next_pixmap'].scaled(
                self.state['next_rect'].size(),
                self.scale_args[0],
                self.scale_args[1],
            )
            if self.scale_args[0] == QtCore.Qt.KeepAspectRatio:
                rect = pixmap.rect()
                rect.moveCenter(self.state['next_rect'].center())
            else:
                crop_rect = QtCore.QRect(self.state['next_rect'])
                crop_rect.moveCenter(pixmap.rect().center())
                pixmap = pixmap.copy(crop_rect)
                rect = self.state['next_rect']

            opacity = 1.0
            self.paintPixmap(rect, pixmap, opacity, painter)


class ImageExpanding(Image):

    css = '''
    background: $transparent;
    '''
    scale_args = (
        QtCore.Qt.KeepAspectRatioByExpanding,
        QtCore.Qt.SmoothTransformation,
    )


def lighten_pixmap(pixmap, amount=150):
    image = pixmap.toImage()
    for x in range(image.width()):
        for y in range(image.height()):
            color = image.pixelColor(x, y)
            image.setPixelColor(x, y, color.lighter(amount))
    return QtGui.QPixmap(image)


@StyledWidget
class ToolButton(QtWidgets.QToolButton):

    css = '''
    background: $transparent;
    '''

    def __init__(self, *args, **kwargs):
        super(ToolButton, self).__init__(*args, **kwargs)
        self._hover = False
        self._pressed = False

    def enterEvent(self, event):
        self._hover = True
        self.update()
        return super(ToolButton, self).enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._pressed = False
        self.update()
        return super(ToolButton, self).leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        return super(ToolButton, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        self.clicked.emit()
        return super(ToolButton, self).mousePressEvent(event)

    def getIconMode(self):
        if not self.isEnabled():
            return QtGui.QIcon.Normal
        if self.isChecked():
            return QtGui.QIcon.Active
        return QtGui.QIcon.Normal

    def getIconState(self):
        if not self.isEnabled():
            return QtGui.QIcon.Off
        return (QtGui.QIcon.Off, QtGui.QIcon.On)[self._hover]

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        rect = self.rect()

        if self.isEnabled():
            rect.moveTop(-int(self._hover) + int(self._pressed))

        icon = self.icon()
        icon.paint(
            painter,
            rect,
            QtCore.Qt.AlignCenter,
            self.getIconMode(),
            self.getIconState(),
        )


@FadeIn
@StyledWidget
class ImageInputControls(QtWidgets.QWidget):

    css = '''
    QWidget{
        background: $dark_overlay;
        color: $light;
        font-size: 14px;
    }
    QLabel{
        background: $transparent;
    }
    '''

    def __init__(self, parent=None):
        super(ImageInputControls, self).__init__(parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )

        # Create widgets
        self.help = QtWidgets.QLabel(
            'Drop, Snip, or Browse for an image.',
            alignment=QtCore.Qt.AlignCenter,
        )
        self.help.setMinimumHeight(px(24))

        # Build Icons
        size = QtCore.QSize(56, 56)
        drop_off = QtGui.QPixmap(ICONS['drop']).scaled(
            size,
            QtCore.Qt.IgnoreAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        drop_on = lighten_pixmap(drop_off, 120)
        drop_icon = QtGui.QIcon()
        drop_icon.addPixmap(drop_off, QtGui.QIcon.Normal, QtGui.QIcon.Off)
        drop_icon.addPixmap(drop_on, QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.drop = ToolButton()
        self.drop.setIcon(drop_icon)
        self.drop.setIconSize(size)
        self.drop.setEnabled(False)

        snip_off = QtGui.QPixmap(ICONS['snip']).scaled(
            size,
            QtCore.Qt.IgnoreAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        snip_on = lighten_pixmap(snip_off, 120)
        snip_icon = QtGui.QIcon()
        snip_icon.addPixmap(snip_off, QtGui.QIcon.Normal, QtGui.QIcon.Off)
        snip_icon.addPixmap(snip_on, QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.snip = ToolButton()
        self.snip.setIcon(snip_icon)
        self.snip.setIconSize(size)

        browse_off = QtGui.QPixmap(ICONS['browse']).scaled(
            size,
            QtCore.Qt.IgnoreAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        browse_on = lighten_pixmap(browse_off, 120)
        browse_icon = QtGui.QIcon()
        browse_icon.addPixmap(browse_off, QtGui.QIcon.Normal, QtGui.QIcon.Off)
        browse_icon.addPixmap(browse_on, QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.browse = ToolButton()
        self.browse.setIcon(browse_icon)
        self.browse.setIconSize(size)

        # Layout widgets
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(4, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(3, 1)
        layout.addWidget(self.help, 1, 1, 1, 3)
        layout.addWidget(self.drop, 2, 1)
        layout.addWidget(self.snip, 2, 2)
        layout.addWidget(self.browse, 2, 3)
        self.setLayout(layout)


@StyledWidget
class ImageInput(QtWidgets.QWidget):
    '''
    An image input widget that supports drag and drop.
    '''

    css = '''
    background: $dark;
    $border_rounded;
    '''

    def __init__(self, image_cls=Image, parent=None):

        super(ImageInput, self).__init__(parent)
        self.setAcceptDrops(True)

        # Create widgets
        self.image = image_cls(parent=self)
        self.controls = ImageInputControls(self)
        self.validator = ImageDropValidator(self)

        self.widgets = QtWidgets.QStackedWidget(self)
        self.widgets.layout().setStackingMode(QtWidgets.QStackedLayout.StackAll)
        self.widgets.addWidget(self.validator)
        self.widgets.addWidget(self.controls)
        self.widgets.addWidget(self.image)

        # Layout widgets
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.widgets)
        self.setLayout(layout)

        # Set Widget initial state
        self.validator.hide()

        # Connect widgets
        self.controls.browse.clicked.connect(self.browseForImage)
        self.controls.snip.clicked.connect(self.snipImage)

        # Attributes
        self._image = None
        self._enter_disabled = False

    def setImage(self, image):
        self._image = image
        self.image.setImage(image, transition=True)
        self.controls.hide()

    def browseForImage(self):
        img_patterns = ' '.join([f'*.{ext}' for ext in IMG_EXTS])
        img_filter = f'Images ({img_patterns})'

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption='Select an image.',
            filter=img_filter,
            parent=self,
        )
        if path:
            self.setImage(path)

    def snipImage(self):
        proportion = None
        if self.minimumHeight() == self.maximumHeight():
            proportion = self.width() / self.height()
        pixmap = select_and_capture(
            proportion=proportion,
            before=self.parent().hide,
            after=self.parent().show,
        )
        if pixmap:
            self.setImage(pixmap)

    def enterEvent(self, event):
        if not self._enter_disabled:
            self.controls.show()
        event.accept()

    def dragEnterEvent(self, event):
        self.validator.show()
        self.controls.hide()
        if self.validator.validate(event.mimeData()):
            event.acceptProposedAction()

        event.accept()

    def leaveEvent(self, event):
        event.accept()
        self.validator.hide()
        self.controls.setVisible(bool(not self._image))

    def dragLeaveEvent(self, event):
        event.accept()
        self.validator.hide()
        self.controls.setVisible(bool(not self._image))

    def dropEvent(self, event):
        images = get_image_paths_from_mime_data(event.mimeData())
        if images and len(images) == 1:
            self.setImage(images[0])
            self._enter_disabled = True
            QtCore.QTimer.singleShot(
                200,
                lambda: setattr(self, '_enter_disabled', False),
            )
        event.acceptProposedAction()
        self.validator.hide()



@StyledWidget
class ExportForm(QtWidgets.QWidget):

    css = '''
    background: $mid;
    '''

    def __init__(self, parent=None):
        super(ExportForm, self).__init__(parent)

        # Create widgets
        self.image_input = ImageInput(Image, self)

        # Layout widgets
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.image_input)
        self.setLayout(layout)


def main():
    app = QtWidgets.QApplication([])
    form = ExportForm()
    form.setWindowFlags(
        form.windowFlags() |
        QtCore.Qt.WindowStaysOnTopHint
    )
    form.show()
    app.exec_()


if __name__ == '__main__':
    main()
