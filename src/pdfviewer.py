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
        self._width = 0
        self._height = 0

    def set_file(self, file):
        document = pymupdf.open(file)
        height = 0
        width = 0
        for page in document.pages():
            height += page.rect.height + self.separator
            width = max(width, page.rect.width)
        self.set_size_request(width, height)
        self.document = document
        self._width = width
        self._height = height

    def do_snapshot(self, snapshot):
        if self.document is None:
            return
        y = 0
        rect = Graphene.Rect().init(0, 0, self._width, self._height)

        print("shot")
        for page in self.document.pages():
            width = page.rect.width
            height = page.rect.height
            rect = Graphene.Rect().init(0, y, width, height)
            y += height + self.separator
            color = Gdk.RGBA()
            color.parse("white")
            snapshot.append_color(color, rect)
            pm = page.get_pixmap()
            RGB = GdkPixbuf.Colorspace.RGB
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(pm.samples, RGB, pm.alpha, 8, pm.width, pm.height, pm.stride)
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            snapshot.append_texture(texture, rect)



