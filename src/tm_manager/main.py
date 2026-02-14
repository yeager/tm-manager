"""Translation Memory Manager - Main application."""

import gettext
import locale
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .tmx import (TMXFile, TranslationUnit, import_po, import_xliff,
                   import_ts, export_po)

# i18n
LOCALE_DIR = Path(__file__).parent.parent.parent / "po"
try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass
gettext.bindtextdomain("tm-manager", str(LOCALE_DIR))
gettext.textdomain("tm-manager")
_ = gettext.gettext


class TMManagerWindow(Adw.ApplicationWindow):
    """Main application window."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tmx = TMXFile()
        self.filtered_units = []
        self.set_title(_("Translation Memory Manager"))
        self.set_default_size(1000, 700)
        self._build_ui()

    def _build_ui(self):
        # Main layout
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(box)

        # Header bar
        header = Adw.HeaderBar()
        box.append(header)

        # Title
        title = Adw.WindowTitle(
            title=_("Translation Memory Manager"),
            subtitle=_("No file loaded"),
        )
        header.set_title_widget(title)
        self._title_widget = title

        # Menu
        menu = Gio.Menu()
        menu.append(_("New TMX"), "app.new")
        menu.append(_("Open TMX…"), "app.open")
        menu.append(_("Save"), "app.save")
        menu.append(_("Save As…"), "app.save_as")

        import_menu = Gio.Menu()
        import_menu.append(_("Import PO…"), "app.import_po")
        import_menu.append(_("Import XLIFF…"), "app.import_xliff")
        import_menu.append(_("Import Qt TS…"), "app.import_ts")
        menu.append_section(_("Import"), import_menu)

        export_menu = Gio.Menu()
        export_menu.append(_("Export as PO…"), "app.export_po")
        menu.append_section(_("Export"), export_menu)

        merge_menu = Gio.Menu()
        merge_menu.append(_("Merge TMX…"), "app.merge")
        menu.append_section(None, merge_menu)

        stats_menu = Gio.Menu()
        stats_menu.append(_("Statistics…"), "app.stats")
        menu.append_section(None, stats_menu)

        about_menu = Gio.Menu()
        about_menu.append(_("About"), "app.about")
        menu.append_section(None, about_menu)

        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_btn)

        # Add segment button
        add_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text=_("Add Segment"))
        add_btn.connect("clicked", self._on_add_segment)
        header.pack_start(add_btn)

        # Search and filter bar
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        filter_box.set_margin_start(12)
        filter_box.set_margin_end(12)
        filter_box.set_margin_top(6)
        filter_box.set_margin_bottom(6)

        self.search_entry = Gtk.SearchEntry(placeholder_text=_("Search translations…"))
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        filter_box.append(self.search_entry)

        # Fuzzy threshold
        self.threshold_spin = Gtk.SpinButton.new_with_range(0.1, 1.0, 0.1)
        self.threshold_spin.set_value(0.6)
        self.threshold_spin.set_tooltip_text(_("Fuzzy match threshold"))
        filter_box.append(self.threshold_spin)

        # Language filter
        self.lang_filter = Gtk.DropDown.new_from_strings([_("All Languages")])
        self.lang_filter.set_tooltip_text(_("Filter by language"))
        self.lang_filter.connect("notify::selected", self._on_filter_changed)
        filter_box.append(self.lang_filter)

        box.append(filter_box)

        # Segment list with scrolling
        scroll = Gtk.ScrolledWindow(vexpand=True)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_placeholder(Gtk.Label(label=_("No segments. Open a TMX file or add segments.")))
        self.listbox.connect("row-activated", self._on_row_activated)
        scroll.set_child(self.listbox)
        box.append(scroll)

        # Status bar
        self.status = Gtk.Label(label=_("Ready"), xalign=0)
        self.status.set_margin_start(12)
        self.status.set_margin_end(12)
        self.status.set_margin_top(4)
        self.status.set_margin_bottom(4)
        self.status.add_css_class("dim-label")
        box.append(self.status)

    def _update_list(self, units=None):
        """Refresh the segment list."""
        while True:
            row = self.listbox.get_row_at_index(0)
            if row is None:
                break
            self.listbox.remove(row)

        display_units = units if units is not None else self.tmx.units
        self.filtered_units = display_units

        for i, unit in enumerate(display_units):
            row = self._create_row(unit, i)
            self.listbox.append(row)

        count = len(display_units)
        total = len(self.tmx.units)
        if units is not None and count != total:
            self.status.set_label(_("{shown} of {total} segments").format(shown=count, total=total))
        else:
            self.status.set_label(_("{total} segments").format(total=total))

    def _create_row(self, unit, index):
        """Create a list row for a translation unit."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # Header with language pair
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lang_label = Gtk.Label(
            label=f"{unit.source_lang} → {unit.target_lang}" if unit.target_lang else unit.source_lang
        )
        lang_label.add_css_class("caption")
        lang_label.add_css_class("dim-label")
        header.append(lang_label)

        if unit.project:
            proj_label = Gtk.Label(label=unit.project)
            proj_label.add_css_class("caption")
            proj_label.add_css_class("accent")
            header.append(proj_label)

        box.append(header)

        # Source text
        src = Gtk.Label(label=unit.source, xalign=0, wrap=True, selectable=True)
        src.add_css_class("heading")
        box.append(src)

        # Target text
        if unit.target:
            tgt = Gtk.Label(label=unit.target, xalign=0, wrap=True, selectable=True)
            tgt.add_css_class("body")
            box.append(tgt)

        row = Gtk.ListBoxRow()
        row.set_child(box)
        row._unit_index = index
        return row

    def _update_lang_filter(self):
        """Update the language dropdown."""
        langs = [_("All Languages")] + self.tmx.get_languages()
        self.lang_filter.set_model(Gtk.StringList.new(langs))

    def _on_search_changed(self, entry):
        query = entry.get_text().strip()
        if not query:
            self._update_list()
            return
        threshold = self.threshold_spin.get_value()
        results = self.tmx.search(query, threshold)
        self._update_list([u for u, _ in results])

    def _on_filter_changed(self, dropdown, _pspec):
        selected = dropdown.get_selected()
        if selected == 0:
            self._update_list()
            return
        langs = self.tmx.get_languages()
        if selected - 1 < len(langs):
            lang = langs[selected - 1]
            filtered = [u for u in self.tmx.units
                        if u.source_lang == lang or u.target_lang == lang]
            self._update_list(filtered)

    def _on_row_activated(self, listbox, row):
        """Edit a segment."""
        if not hasattr(row, "_unit_index"):
            return
        idx = row._unit_index
        if idx < len(self.filtered_units):
            unit = self.filtered_units[idx]
            self._show_edit_dialog(unit)

    def _show_edit_dialog(self, unit):
        """Show dialog to edit a translation unit."""
        dialog = Adw.Dialog()
        dialog.set_title(_("Edit Segment"))
        dialog.set_content_width(500)
        dialog.set_content_height(400)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        save_btn = Gtk.Button(label=_("Save"))
        save_btn.add_css_class("suggested-action")
        header.pack_end(save_btn)

        delete_btn = Gtk.Button(label=_("Delete"))
        delete_btn.add_css_class("destructive-action")
        header.pack_start(delete_btn)

        page = Adw.PreferencesPage()

        group = Adw.PreferencesGroup(title=_("Translation"))

        src_row = Adw.EntryRow(title=_("Source"))
        src_row.set_text(unit.source)
        group.add(src_row)

        tgt_row = Adw.EntryRow(title=_("Target"))
        tgt_row.set_text(unit.target)
        group.add(tgt_row)

        src_lang_row = Adw.EntryRow(title=_("Source Language"))
        src_lang_row.set_text(unit.source_lang)
        group.add(src_lang_row)

        tgt_lang_row = Adw.EntryRow(title=_("Target Language"))
        tgt_lang_row.set_text(unit.target_lang)
        group.add(tgt_lang_row)

        note_row = Adw.EntryRow(title=_("Note"))
        note_row.set_text(unit.note or "")
        group.add(note_row)

        project_row = Adw.EntryRow(title=_("Project"))
        project_row.set_text(unit.project or "")
        group.add(project_row)

        page.add(group)
        toolbar_view.set_content(page)
        dialog.set_child(toolbar_view)

        def on_save(_btn):
            unit.source = src_row.get_text()
            unit.target = tgt_row.get_text()
            unit.source_lang = src_lang_row.get_text()
            unit.target_lang = tgt_lang_row.get_text()
            unit.note = note_row.get_text()
            unit.project = project_row.get_text()
            self.tmx.modified = True
            self._update_list()
            self._update_lang_filter()
            dialog.close()

        def on_delete(_btn):
            idx = self.tmx.units.index(unit) if unit in self.tmx.units else -1
            if idx >= 0:
                self.tmx.remove_unit(idx)
            self._update_list()
            self._update_lang_filter()
            dialog.close()

        save_btn.connect("clicked", on_save)
        delete_btn.connect("clicked", on_delete)
        dialog.present(self)

    def _on_add_segment(self, _btn):
        """Add a new translation segment."""
        unit = TranslationUnit(source_lang=self.tmx.source_lang)
        self.tmx.add_unit(unit)
        self._update_list()
        self._show_edit_dialog(unit)

    def load_file(self, path):
        """Load a TMX file."""
        try:
            self.tmx.load(path)
            self._title_widget.set_subtitle(Path(path).name)
            self._update_list()
            self._update_lang_filter()
            self.status.set_label(_("{total} segments loaded from {file}").format(
                total=len(self.tmx.units), file=Path(path).name))
        except Exception as e:
            self._show_error(_("Failed to load file"), str(e))

    def _show_error(self, title, message):
        dialog = Adw.AlertDialog(heading=title, body=message)
        dialog.add_response("ok", _("OK"))
        dialog.present(self)


class TMManagerApp(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="se.danielnylander.TMManager",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self.win = None

    def do_activate(self):
        if not self.win:
            self.win = TMManagerWindow(application=self)
            self._setup_actions()
        self.win.present()

    def do_open(self, files, n_files, hint):
        self.do_activate()
        if files:
            self.win.load_file(files[0].get_path())

    def _setup_actions(self):
        actions = {
            "new": self._on_new,
            "open": self._on_open,
            "save": self._on_save,
            "save_as": self._on_save_as,
            "import_po": self._on_import_po,
            "import_xliff": self._on_import_xliff,
            "import_ts": self._on_import_ts,
            "export_po": self._on_export_po,
            "merge": self._on_merge,
            "stats": self._on_stats,
            "about": self._on_about,
        }
        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def _on_new(self, *_args):
        self.win.tmx = TMXFile()
        self.win._title_widget.set_subtitle(_("New file"))
        self.win._update_list()
        self.win._update_lang_filter()

    def _on_open(self, *_args):
        dialog = Gtk.FileDialog()
        f = Gtk.FileFilter()
        f.set_name(_("TMX files"))
        f.add_pattern("*.tmx")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self.win, None, self._on_open_response)

    def _on_open_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.win.load_file(file.get_path())
        except GLib.Error:
            pass

    def _on_save(self, *_args):
        if self.win.tmx.path:
            try:
                self.win.tmx.save()
                self.win.status.set_label(_("Saved"))
            except Exception as e:
                self.win._show_error(_("Save failed"), str(e))
        else:
            self._on_save_as()

    def _on_save_as(self, *_args):
        dialog = Gtk.FileDialog()
        f = Gtk.FileFilter()
        f.set_name(_("TMX files"))
        f.add_pattern("*.tmx")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.save(self.win, None, self._on_save_as_response)

    def _on_save_as_response(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                path = file.get_path()
                if not path.endswith(".tmx"):
                    path += ".tmx"
                self.win.tmx.save(path)
                self.win._title_widget.set_subtitle(Path(path).name)
                self.win.status.set_label(_("Saved to {file}").format(file=Path(path).name))
        except GLib.Error:
            pass

    def _on_import_po(self, *_args):
        self._import_file(_("PO files"), "*.po", "po")

    def _on_import_xliff(self, *_args):
        self._import_file(_("XLIFF files"), "*.xliff", "xliff")

    def _on_import_ts(self, *_args):
        self._import_file(_("Qt TS files"), "*.ts", "ts")

    def _import_file(self, filter_name, pattern, fmt):
        dialog = Gtk.FileDialog()
        f = Gtk.FileFilter()
        f.set_name(filter_name)
        f.add_pattern(pattern)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self.win, None, lambda d, r: self._on_import_response(d, r, fmt))

    def _on_import_response(self, dialog, result, fmt):
        try:
            file = dialog.open_finish(result)
            if not file:
                return
            path = file.get_path()
            if fmt == "po":
                units = import_po(path)
            elif fmt == "xliff":
                units = import_xliff(path)
            elif fmt == "ts":
                units = import_ts(path)
            else:
                return
            for u in units:
                self.win.tmx.add_unit(u)
            self.win._update_list()
            self.win._update_lang_filter()
            self.win.status.set_label(_("Imported {count} segments").format(count=len(units)))
        except GLib.Error:
            pass
        except Exception as e:
            self.win._show_error(_("Import failed"), str(e))

    def _on_export_po(self, *_args):
        dialog = Gtk.FileDialog()
        f = Gtk.FileFilter()
        f.set_name(_("PO files"))
        f.add_pattern("*.po")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.save(self.win, None, self._on_export_po_response)

    def _on_export_po_response(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                path = file.get_path()
                if not path.endswith(".po"):
                    path += ".po"
                export_po(self.win.tmx.units, path)
                self.win.status.set_label(_("Exported to {file}").format(file=Path(path).name))
        except GLib.Error:
            pass

    def _on_merge(self, *_args):
        dialog = Gtk.FileDialog()
        f = Gtk.FileFilter()
        f.set_name(_("TMX files"))
        f.add_pattern("*.tmx")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self.win, None, self._on_merge_response)

    def _on_merge_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                other = TMXFile(file.get_path())
                added = self.win.tmx.merge(other)
                self.win._update_list()
                self.win._update_lang_filter()
                self.win.status.set_label(_("Merged: {added} new segments added").format(added=added))
        except GLib.Error:
            pass
        except Exception as e:
            self.win._show_error(_("Merge failed"), str(e))

    def _on_stats(self, *_args):
        stats = self.win.tmx.get_stats()
        pairs = ", ".join(f"{s}→{t}" for s, t in stats["language_pairs"]) or _("None")
        projects = ", ".join(stats["projects"]) or _("None")
        body = _(
            "Total segments: {total}\n"
            "Languages: {langs}\n"
            "Language pairs: {pairs}\n"
            "Projects: {projects}"
        ).format(
            total=stats["total_segments"],
            langs=", ".join(stats["languages"]) or _("None"),
            pairs=pairs,
            projects=projects,
        )
        dialog = Adw.AlertDialog(heading=_("Statistics"), body=body)
        dialog.add_response("ok", _("OK"))
        dialog.present(self.win)

    def _on_about(self, *_args):
        about = Adw.AboutDialog(
            application_name=_("Translation Memory Manager"),
            application_icon="accessories-text-editor",
            version="0.1.0",
            developer_name="Daniel Nylander",
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/yeager/tm-manager",
            issue_url="https://github.com/yeager/tm-manager/issues",
            comments=_("Manage local Translation Memory files"),
        )
        about.present(self.win)


def main():
    app = TMManagerApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
