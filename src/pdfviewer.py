import gi
from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Graphene
from gi.repository import GdkPixbuf
import pymupdf

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/pdfviewer.ui')
class PdfViewer(Gtk.Widget):
    __gtype_name__ = 'PdfViewer'

    stack = Gtk.Template.Child()
    box = Gtk.Template.Child()
    scroll = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)
        self._path = None
        self.zoom = 0.4 # zoom factor when not in zoom gesture
        self.zoom_delta = 1 # keep zoom level delta while zooming
        self.mouse_x = 0 # keep the pointer coordinate
        self.mouse_y = 0 # keep the pointer coordinate
        self.vadj = 0 # keep hadj, vadj
        self.hadj = 0

        controller = Gtk.GestureZoom.new()
        controller.connect("scale-changed", self.on_zoom)
        controller.connect("begin", self.on_zoom_begin)
        controller.connect("end", self.on_zoom_end)
        self.add_controller(controller)

        controller = Gtk.EventControllerMotion.new()
        controller.connect("motion", self.on_motion)
        self.add_controller(controller)

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
            page = PdfPage(p, self.zoom)
            overlay = Gtk.Overlay()
            overlay.set_child(page)
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
            rect = SynctexRect(w,h,x,y, page.scale*200/72)
            overlay.add_overlay(rect)

        _, _, _, y, p = rects[0]
        overlay = self.get_page(p)
        if overlay is None:
            return
        page = overlay.get_child()
        self.scroll_to(p, (y-h)*page.scale)

    def on_zoom(self, zoom_gesture, scale):
        p = self.box.get_first_child()
        while p is not None:
            p.get_child().zoom(self.zoom*scale)
            p = p.get_next_sibling()
        hadj = self.scroll.get_hadjustment()
        vadj = self.scroll.get_vadjustment()
        hadj.set_value(max(0,(self.hadj+self.mouse_x)*scale - self.mouse_x))
        vadj.set_value(max(0,(self.vadj+self.mouse_y)*scale - self.mouse_y))
        self.zoom_delta = scale

    def on_zoom_begin(self, zoom_gesture, sequence):
        self.hadj = self.scroll.get_hadjustment().get_value()
        self.vadj = self.scroll.get_vadjustment().get_value()


    def on_zoom_end(self, zoom_gesture, sequence):
        self.zoom = self.zoom* self.zoom_delta

    def on_motion(self, controller, x, y):
        self.mouse_x = x
        self.mouse_y = y

class PdfPage(Gtk.Widget):
    __gtype_name__ = 'PdfPage'

    def __init__(self, page, initial_scale):
        super().__init__()
        self.page = page
        self.scale = initial_scale
        self.render()

    def zoom(self,zoom):
        self.scale = zoom
        self.queue_resize()
        self.queue_draw()

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
