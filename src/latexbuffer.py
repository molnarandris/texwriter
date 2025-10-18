import gi
gi.require_version("GtkSource", "5")
from gi.repository import GtkSource
from gi.repository import Gtk
import re


class LatexBuffer(GtkSource.Buffer):

    def __init__(self):
        super().__init__()
        self.command_tag = self.create_tag("command", foreground="#cf222e")

    def highlight_commands(self, start, end):
        self.remove_all_tags(start, end)
        txt = self.get_text(start, end, True)
        command_regex = r'\\[a-zA-Z]+'
        for m in re.finditer(command_regex, txt):
            start_it = start.copy()
            start_it.forward_chars(m.start())
            end_it = start.copy()
            end_it.forward_chars(m.end())
            self.apply_tag(self.command_tag, start_it, end_it)

    def do_changed(self):
        insert = self.get_insert()
        start = self.get_iter_at_mark(insert)
        start.backward_line()
        end = self.get_iter_at_mark(insert)
        end.forward_line()
        self.highlight_commands(start, end)



