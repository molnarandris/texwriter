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

        RGB = GdkPixbuf.Colorspace.RGB
        for p in document.pages():
            pm = p.get_pixmap()
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(pm.samples, RGB, pm.alpha, 8, pm.width, pm.height, pm.stride)
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            pic = Gtk.Picture.new_for_paintable(texture)
            pic.set_can_shrink(False)
            self.box.append(pic)
