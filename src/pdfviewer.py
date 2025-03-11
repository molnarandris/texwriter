import gi
import pymupdf
from gi.repository import Gtk, Adw
from gi.repository import Graphene, Gdk, GdkPixbuf, GLib

@Gtk.Template(resource_path='/io/github/molnarandris/TeXWriter/pdfviewer.ui')
class PdfViewer(Gtk.Widget):
    __gtype_name__ = "PdfViewer"

    stack = Gtk.Template.Child()
    box = Gtk.Template.Child()
    scroll = Gtk.Template.Child()

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
        child = self.box.get_first_child()
        for i in range(n):
            child = child.get_next_sibling()
        return child

    def scroll_to(self, page_num, y):
        overlay = self.get_page(page_num)
        if overlay is None:
            return
        page = overlay.get_child()
        point = Graphene.Point()
        point.init(0, y)
        _, p = page.compute_point(self.box, point)
        vadj = self.scroll.get_vadjustment()
        vadj.set_value(p.y - self.scroll.get_height()*0.3)

    def synctex_fwd(self, rects):
        for r in rects:
            w,h,x,y,p = r
            overlay = self.get_page(p)
            if overlay is None:
                return
            page = overlay.get_child()
            rect = SynctexRect(w,h,x,y, page.scale)
            overlay.add_overlay(rect)

        _, _, _, y, p = rects[0]
        overlay = self.get_page(p)
        if overlay is None:
            return
        page = overlay.get_child()
        self.scroll_to(p, (y-h)*page.scale)

class PdfPage(Gtk.Widget):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.texture = None
        self._ratio = page.rect.height/page.rect.width

    @property
    def scale(self):
        return self.get_width()/self.page.rect.width

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
        self.render(self.scale) # TODO remove from here
        if self.texture:
            snapshot.append_texture(self.texture, rect)

class SynctexRect(Gtk.Widget):
    __gtype_name__ = 'SynctexRect'

    def __init__(self, width, height, x, y, scale):
        super().__init__()
        height += 2
        self.color = Gdk.RGBA()
        self.color.parse("#FFF38060")
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)
        self.set_margin_top((y-height+1)*scale)
        self.set_margin_start(x*scale)
        GLib.timeout_add(700, self.do_destroy)
        self.set_size_request(width*scale, height*scale)

    def do_snapshot(self, snapshot):
        rect = Graphene.Rect().init(0, 0, self.get_width(), self.get_height())
        snapshot.append_color(self.color, rect)

    def do_destroy(self):
        self.unparent()
        return False
