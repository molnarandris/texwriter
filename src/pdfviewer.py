import gi
from gi.repository import Gtk
gi.require_version('Poppler', '0.18')
from gi.repository import Poppler
from gi.repository import Graphene, Gdk

@Gtk.Template(resource_path='/io/github/molnarandris/TeXWriter/pdfviewer.ui')
class PdfViewer(Gtk.Widget):
    __gtype_name__ = "PdfViewer"

    def __init__(self):
        super().__init__()
        self.document = None

    def set_file(self, file):
        self.document = Poppler.Document.new_from_file("file://" + file)

    def do_snapshot(self, snapshot):
        if self.document is None:
            return
        page = self.document.get_page(0)
        width, height = page.get_size()
        rect = Graphene.Rect().init(0, 0, width, height)
        color = Gdk.RGBA()
        color.parse("white")
        snapshot.append_color(color, rect)
        ctx = snapshot.append_cairo(rect)
        page.render(ctx)

