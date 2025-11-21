import gi
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GtkSource
from .latexbuffer import LatexBuffer
from gi.repository import Gio


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

        #self.add_completion("/app/share/completion/latex-mathsymbols.cwl")
        self.add_completion("/app/share/completion/latex-document.cwl")
        completion = self.source_view.get_completion()
        completion.set_property("select-on-show", True)

    def add_completion(self, path):
        file = Gio.File.new_for_path(path)
        contents = file.load_contents()
        keywords = contents[1].decode('utf-8')
        provider = MyCompletion('latex-math')
        provider.set_keywords(keywords)
        completion = self.source_view.get_completion()
        completion.add_provider(provider)

    def set_text(self, text):
        buffer = self.source_view.get_buffer()
        buffer.set_text(text)
        start, end = buffer.get_bounds()
        #buffer.highlight_commands(start, end)
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

    def scroll_to(self, line):
        buffer = self.source_view.get_buffer()
        _, it = buffer.get_iter_at_line(line-1)
        bound = it.copy()
        bound.forward_to_line_end()

        if line == 0:
            return

        #match_start, match_end = it.forward_search(text_before, Gtk.TextSearchFlags.TEXT_ONLY, bound)
        #buffer.apply_tag_by_name('highlight', *result)
        #GLib.timeout_add(500, lambda: buffer.remove_tag_by_name('highlight',*result))
        #it = result[0]
        self.source_view.scroll_to_iter(it, 0.3, False, 0, 0)
        buffer.place_cursor(it)
        self.source_view.grab_focus()


class MyCompletion(GObject.Object, GtkSource.CompletionProvider):
    __gtype_name__ = "MyCompletion"

    def __init__(self, title):
        super().__init__()
        self._title = title
        self.keyword_list = MyCompletionModel()
        self._filter_data = FilterData()

    def set_keywords(self, keywords):
        for line in keywords.splitlines():
            word = Word(line)
            self.keyword_list.add(word)

    def do_activate(self, context, proposal):
        buffer = context.get_buffer()
        _, start, end = context.get_bounds()
        start.backward_char()
        buffer.delete(start,end) # delete re-initializes start and end
        word = proposal.word
        buffer.insert(start, word, len(word))

    def do_display(self,context, proposal, cell):
        if cell.get_column() == GtkSource.CompletionColumn.TYPED_TEXT:
            cell.set_text(proposal.word)

    def do_get_priority(self, context):
        return 0

    def do_get_title(self):
        return self._title

    def do_is_trigger(self, it, ch):
        if ch == '\\':
            return True
        else:
            return False

    def do_populate_async(self, context, cancellable, callback, user_data):
        # hack using https://gitlab.gnome.org/GNOME/pygobject/-/issues/710#note_2520410
        # See also https://github.com/gaphor/gaphor/blob/294afd7f31f0154f8600098336892ae8dc16eea6/gaphor/ui/csscompletion.py#L121

        # This is non-async implementation.
        # To make it async I can really just spawn an async process.
        # Note that this hack introduces memory leaks.

        has_selection, start, end = context.get_bounds()
        start.backward_char()
        if start.get_char() != "\\":
            return

        self._filter_word = "\\" + context.get_word()
        def filter_fn(proposal, filter_data):
            return proposal.word.startswith(filter_data.word)

        store_filter = Gtk.CustomFilter.new(filter_fn, self._filter_data)
        proposals = Gtk.FilterListModel.new(self.keyword_list, store_filter)
        context.set_proposals_for_provider(self, proposals)

    def do_refilter(self, context, model):
        word = "\\" + context.get_word()
        change = Gtk.FilterChange.DIFFERENT
        if old_word := self._filter_data.word:
            if word.startswith(old_word):
                change = Gtk.FilterChange.MORE_STRICT
            elif old_word.startswith(word):
                change = Gtk.FilterChange.LESS_STRICT
        self._filter_data.word = word
        model.get_filter().changed(change)


class Word(GObject.Object, GtkSource.CompletionProposal):
    __gtype_name__ = "Word"

    name = GObject.Property(type=str)

    def __init__(self, word):
        super().__init__()
        self.word = word

class MyCompletionModel(GObject.GObject, Gio.ListModel):
    __gtype_name__ = "MyCompletionModel"

    def __init__(self):
        super().__init__()
        self._list = []

    def do_get_item(self, position):
        return self._list[position]

    def do_get_item_type(self):
        return Word

    def do_get_n_items(self):
        return len(self._list)

    def add(self, word):
        self._list.append(word)
        self.items_changed(len(self._list) - 1, 0, 1)

    def remove(self, position):
        del self._list[position]
        self.items_changed(position, 1, 0)

    def get_index_by_string(self, content):
        for i, word in enumerate(self._item):
            if word.word == content:
                return i
        return None

class FilterData:
    word = ""
