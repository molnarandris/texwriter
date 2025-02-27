import gi
import pymupdf
from gi.repository import Gtk, Adw
from gi.repository import Graphene, Gdk, GdkPixbuf

@Gtk.Template(resource_path='/io/github/molnarandris/TeXWriter/pdfviewer.ui')
class PdfViewer(Gtk.Widget):
    __gtype_name__ = "PdfViewer"

    stack = Gtk.Template.Child()
    viewer = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)

    def set_file(self, file):
        if self.viewer.set_file(file):
            self.stack.set_visible_child_name("pdf")
        else:
            self.stack.set_visible_child_name("empty")


class _PdfViewer(Gtk.Widget):
    __gtype_name__ = "_PdfViewer"

    def __init__(self):
        super().__init__()
        self.separator = 5
        self.set_empty_state()

    def set_empty_state(self):
        self.document = None
        self._pdf_width = 0
        self._ratio = 1
        self.queue_resize()
        self.queue_draw()

    def set_file(self, file):
        if file is None:
            self.set_empty_state()
            return False
        try:
            document = pymupdf.open(file)
        except pymupdf.FileNotFoundError:
            self.set_empty_state()
            return False
        height = 0
        width = 0
        for page in document.pages():
            height += page.rect.height + self.separator
            width = max(width, page.rect.width)
        self.document = document
        self._pdf_width = width
        assert width != 0
        self._ratio = height/width
        self.queue_resize()
        self.queue_draw()
        return True

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_measure(self, orientation, for_size):
        if orientation == Gtk.Orientation.HORIZONTAL:
            minimum = 0
            natural = int(for_size / self._ratio)
        else:
            minimum = int(for_size * self._ratio)
            natural = int(for_size * self._ratio)
        minimum_baseline = -1
        natural_baseline = -1
        return minimum, natural, minimum_baseline, natural_baseline

    def do_snapshot(self, snapshot):
        if self.document is None:
            return
        scale = self.get_width()/self._pdf_width
        mx = pymupdf.Matrix(scale, scale)

        y = 0
        for page in self.document.pages():
            width = page.rect.width*scale
            height = page.rect.height*scale
            rect = Graphene.Rect().init(0, y, width, height)
            y += height + self.separator
            color = Gdk.RGBA()
            color.parse("white")
            snapshot.append_color(color, rect)
            pm = page.get_pixmap(matrix=mx)
            RGB = GdkPixbuf.Colorspace.RGB
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(pm.samples, RGB, pm.alpha, 8, pm.width, pm.height, pm.stride)
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            snapshot.append_texture(texture, rect)



