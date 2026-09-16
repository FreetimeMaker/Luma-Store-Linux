#!/usr/bin/env python3
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio


APPS = [
    {"name": "GeoWeather", "summary": "A simple weather app for Android, Windows and Linux.", "category": "Weather", "version": "2.3.0"},
    {"name": "SuperSMP Companion", "summary": "Companion app for the SuperSMP community.", "category": "Games", "version": "1.0"},
    {"name": "Programming Language Clicker", "summary": "A clicker game about programming languages.", "category": "Games", "version": "1.0.3"},
    {"name": "Luma Store", "summary": "The Freetime Maker app store.", "category": "System", "version": "0.1.0"},
]


class LumaStoreWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Luma Store")
        self.set_default_size(960, 680)

        header = Gtk.HeaderBar(title="Luma Store", subtitle="Apps for Linux", show_close_button=True)
        self.set_titlebar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        nav.set_margin_start(12)
        nav.set_margin_end(12)
        nav.set_margin_top(8)
        nav.set_margin_bottom(8)
        root.pack_start(nav, False, False, 0)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT, transition_duration=180)
        root.pack_start(self.stack, True, True, 0)

        for label, page in (("Discover", "discover"), ("Search", "search"), ("Categories", "categories")):
            button = Gtk.Button(label=label)
            button.connect("clicked", lambda _b, name=page: self.stack.set_visible_child_name(name))
            nav.pack_start(button, False, False, 0)

        self.stack.add_named(self.make_discover_page(), "discover")
        self.stack.add_named(self.make_search_page(), "search")
        self.stack.add_named(self.make_categories_page(), "categories")
        self.stack.add_named(self.make_details_page(), "details")
        self.stack.set_visible_child_name("discover")

        css = Gtk.CssProvider()
        css.load_from_data(b".page-title { font-size: 24px; font-weight: bold; } .app-name { font-size: 16px; font-weight: bold; } list row { border-bottom: 1px solid alpha(currentColor, 0.12); }")
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    @staticmethod
    def page_box(spacing=14):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
        for setter in (box.set_margin_start, box.set_margin_end, box.set_margin_top, box.set_margin_bottom):
            setter(24)
        return box

    @staticmethod
    def heading(text):
        label = Gtk.Label(label=text, xalign=0)
        label.get_style_context().add_class("page-title")
        return label

    def make_discover_page(self):
        outer = self.page_box(18)
        outer.pack_start(self.heading("Discover Linux apps"), False, False, 0)
        outer.pack_start(Gtk.Label(label="Browse apps available in Luma Store.", xalign=0), False, False, 0)
        app_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        for app in APPS:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            row_box.set_border_width(12)
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            name = Gtk.Label(label=app["name"], xalign=0)
            name.get_style_context().add_class("app-name")
            text.pack_start(name, False, False, 0)
            text.pack_start(Gtk.Label(label=app["summary"], xalign=0, ellipsize=3), False, False, 0)
            button = Gtk.Button(label="View")
            button.connect("clicked", self.show_details, app)
            row_box.pack_start(text, True, True, 0)
            row_box.pack_end(button, False, False, 0)
            row = Gtk.ListBoxRow()
            row.add(row_box)
            app_list.add(row)
        outer.pack_start(app_list, True, True, 0)
        return outer

    def make_search_page(self):
        outer = self.page_box()
        outer.pack_start(self.heading("Search"), False, False, 0)
        entry = Gtk.SearchEntry()
        outer.pack_start(entry, False, False, 0)
        self.search_results = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        outer.pack_start(self.search_results, True, True, 0)
        entry.connect("search-changed", self.on_search_changed)
        return outer

    def on_search_changed(self, entry):
        for child in self.search_results.get_children():
            self.search_results.remove(child)
        query = entry.get_text().strip().lower()
        if query:
            for app in APPS:
                if query in app["name"].lower() or query in app["summary"].lower():
                    button = Gtk.Button(label=f'{app["name"]} — {app["summary"]}')
                    button.connect("clicked", self.show_details, app)
                    row = Gtk.ListBoxRow()
                    row.add(button)
                    self.search_results.add(row)
        self.search_results.show_all()

    def make_categories_page(self):
        outer = self.page_box()
        outer.pack_start(self.heading("Categories"), False, False, 0)
        for category in ("Games", "Weather", "System", "Utilities", "Development"):
            outer.pack_start(Gtk.Button(label=category), False, False, 0)
        return outer

    def make_details_page(self):
        outer = self.page_box(16)
        back = Gtk.Button(label="← Back to Discover")
        back.set_halign(Gtk.Align.START)
        back.connect("clicked", lambda _b: self.stack.set_visible_child_name("discover"))
        outer.pack_start(back, False, False, 0)
        self.details_title = self.heading("App")
        self.details_summary = Gtk.Label(xalign=0, wrap=True)
        self.details_meta = Gtk.Label(xalign=0)
        outer.pack_start(self.details_title, False, False, 0)
        outer.pack_start(self.details_summary, False, False, 0)
        outer.pack_start(self.details_meta, False, False, 0)
        install = Gtk.Button(label="Install")
        install.set_halign(Gtk.Align.START)
        install.get_style_context().add_class("suggested-action")
        outer.pack_start(install, False, False, 0)
        return outer

    def show_details(self, _button, app):
        self.details_title.set_text(app["name"])
        self.details_summary.set_text(app["summary"])
        self.details_meta.set_text(f'Category: {app["category"]}  •  Version: {app["version"]}')
        self.stack.set_visible_child_name("details")


class LumaStore(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.freetime.LumaStore", flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        window = self.props.active_window or LumaStoreWindow(self)
        window.show_all()
        window.present()


if __name__ == "__main__":
    raise SystemExit(LumaStore().run(None))
