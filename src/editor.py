import gi
from gi.repository import Gtk


@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/editor.ui')
class Editor(Gtk.Widget):
    __gtype_name__ = 'Editor'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

