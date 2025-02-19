import gi
import pymupdf
from gi.repository import Gtk
from gi.repository import Graphene, Gdk, GdkPixbuf

@Gtk.Template(resource_path='/io/github/molnarandris/TeXWriter/pdfviewer.ui')
class PdfViewer(Gtk.Widget):
    __gtype_name__ = "PdfViewer"

    def __init__(self):
        super().__init__()
        self.document = None
        self.separator = 5
        self._pdf_width = 0
        self._pdf_height = 0
        self._ratio = 1

    def set_file(self, file):
        document = pymupdf.open(file)
        height = 0
        width = 0
        for page in document.pages():
            height += page.rect.height + self.separator
            width = max(width, page.rect.width)
        self.document = document
        self._pdf_width = width
        self._pdf_height = height
        self._ratio = height/width
        self.queue_draw()

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



