import gi
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GtkSource
from .latexbuffer import LatexBuffer


GtkSource.init()

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/editor.ui')
class Editor(Gtk.Widget):
    __gtype_name__ = 'Editor'
    __gsignals__ = {
            'modified-changed': (GObject.SIGNAL_RUN_FIRST, None, (bool,))
        }
    source_view = Gtk.Template.Child()
    banner = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)

        buffer = LatexBuffer()
        self.source_view.set_buffer(buffer)
        buffer.connect("modified-changed", self.on_buffer_modified_changed)

    def set_text(self, text):
        buffer = self.source_view.get_buffer()
        buffer.set_text(text)
        start, end = buffer.get_bounds()
        buffer.highlight_commands(start, end)
        start = buffer.get_start_iter()
        buffer.place_cursor(start)
        buffer.set_modified(False)

    def get_text(self):
        buffer = self.source_view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        return buffer.get_text(start, end, False)

    def set_modified(self, modified):
        buffer = self.source_view.get_buffer()
        buffer.set_modified(modified)

    def get_cursor_position(self):
        buffer = self.source_view.get_buffer()
        it = buffer.get_iter_at_mark(buffer.get_insert())
        line = it.get_line()
        column = it.get_line_offset()
        return line, column

    def on_buffer_modified_changed(self, buffer):
        self.emit("modified-changed", buffer.get_modified())

    @Gtk.Template.Callback()
    def on_banner_button_clicked(self, user_data):
        self.banner.set_revealed(False)
        create_task(self.open(self._file.file))


