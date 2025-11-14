import gi
from gi.repository import Adw
from gi.repository import Gtk

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/preferences.ui')
class PreferencesWindow(Adw.PreferencesDialog):
    __gtype_name__ = "PreferencesWindow"

    def __init__(self):
        super().__init__()


