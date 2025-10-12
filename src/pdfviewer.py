import gi
from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import pymupdf

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/pdfviewer.ui')
class PdfViewer(Gtk.Widget):
    __gtype_name__ = 'PdfViewer'

    stack = Gtk.Template.Child()
    box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)
        self._path = None

    def set_path(self,path):
        self._path = path
        self.reload()

    def show_empty(self):
        self.stack.set_visible_child_name("empty")

    def reload(self):
        try:
            document = pymupdf.open(self._path)
        except pymupdf.FileNotFoundError:
            self.stack.set_visible_child_name("empty")
            return

        self.stack.set_visible_child_name("content")

        p = self.box.get_first_child()
        while p is not None:
            self.box.remove(p)
            p = self.box.get_first_child()

        for p in document.pages():
            page = PdfPage(p)
            self.box.append(page)


class PdfPage(Gtk.Widget):
    __gtype_name__ = 'PdfPage'

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.scale = 0.4
        self.render()

    def render(self):
        RGB = GdkPixbuf.Colorspace.RGB
        pm = self.page.get_pixmap(dpi = 200)
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(pm.samples, RGB, pm.alpha, 8, pm.width, pm.height, pm.stride)
        self.texture = Gdk.Texture.new_for_pixbuf(pixbuf)

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_snapshot(self, snapshot):
        width = self.texture.get_intrinsic_width() * self.scale
        height = self.texture.get_intrinsic_height() * self.scale
        self.texture.snapshot(snapshot, width, height)

    def do_measure(self, orientation, for_size):
        if orientation == Gtk.Orientation.HORIZONTAL:
            width = self.texture.get_intrinsic_width() * self.scale
            return (width, width, -1, -1)
        else:
            height = self.texture.get_intrinsic_height() * self.scale
            return (height, height, -1, -1)

