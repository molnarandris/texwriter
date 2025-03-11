import gi
import pymupdf
from gi.repository import Gtk, Adw
from gi.repository import Graphene, Gdk, GdkPixbuf

@Gtk.Template(resource_path='/io/github/molnarandris/TeXWriter/pdfviewer.ui')
class PdfViewer(Gtk.Widget):
    __gtype_name__ = "PdfViewer"

    stack = Gtk.Template.Child()
    box = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)
        self.scale = 1
        self.box.set_spacing(5)
        self.box.set_orientation(Gtk.Orientation.VERTICAL)

    def set_file(self, file):
        if file is None:
            self.stack.set_visible_child_name("empty")
        try:
            document = pymupdf.open(file)
        except pymupdf.FileNotFoundError:
            self.stack.set_visible_child_name("empty")
        else:
            self.stack.set_visible_child_name("pdf")
            overlay = self.box.get_first_child()
            while overlay is not None:
                self.box.remove(overlay)
                pg = overlay.get_child()
                pg.unparent()
                overlay.set_child(None)
                overlay = self.box.get_first_child()
            for pg in document.pages():
                overlay = Gtk.Overlay()
                overlay.set_child(PdfPage(pg))
                self.box.append(overlay)

    def get_page(self, n):
        child = self.get_first_child()
        for i in range(n):
            child = child.get_next_sibling()
        return child


class PdfPage(Gtk.Widget):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.texture = None
        self._ratio = page.rect.height/page.rect.width

    def render(self, scale):
        mx = pymupdf.Matrix(scale, scale)
        pm = self.page.get_pixmap(matrix=mx)
        RGB = GdkPixbuf.Colorspace.RGB
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(pm.samples, RGB, pm.alpha, 8, pm.width, pm.height, pm.stride)
        self.texture = Gdk.Texture.new_for_pixbuf(pixbuf)

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
        width = self.get_width()
        height = int(width*self._ratio)
        rect = Graphene.Rect().init(0, 0, width, height)
        color = Gdk.RGBA()
        color.parse("white")
        snapshot.append_color(color, rect)
        self.render(self.get_width()/self.page.rect.width) # TODO remove from here
        if self.texture:
            snapshot.append_texture(self.texture, rect)

