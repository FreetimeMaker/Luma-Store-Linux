#!/usr/bin/env python3
import json
import os
import re
import threading
import urllib.parse
import urllib.request
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, GdkPixbuf

API_BASE = "https://api.free-time.me/v2/lumastore"
PLATFORM = "linux"
APPIMAGE_DIR = Path.home() / ".local" / "bin" / "luma-store-appimages"


class LumaApi:
    @staticmethod
    def _get(path, params=None):
        query = urllib.parse.urlencode(params or {})
        url = f"{API_BASE}{path}" + (f"?{query}" if query else "")
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Luma-Store-Linux/0.1"})
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    @classmethod
    def apps(cls, search=None):
        params = {"platform": PLATFORM}
        if search:
            params["search"] = search
        return cls._get("/apps", params)

    @classmethod
    def app(cls, app_id):
        return cls._get(f"/apps/{urllib.parse.quote(str(app_id), safe='')}", {"platform": PLATFORM})


class LumaStoreWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Luma Store")
        self.set_default_size(960, 680)
        self.apps = []
        self.current_app = None

        header = Gtk.HeaderBar(title="Luma Store", subtitle="Apps for Linux", show_close_button=True)
        self.set_titlebar(header)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        nav.set_border_width(8)
        root.pack_start(nav, False, False, 0)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT, transition_duration=180)
        root.pack_start(self.stack, True, True, 0)
        for label, page in (("Discover", "discover"), ("Search", "search"), ("Categories", "categories")):
            button = Gtk.Button(label=label)
            if page == "discover":
                button.connect("clicked", lambda _b: self.reset_and_show_discover())
            else:
                button.connect("clicked", lambda _b, name=page: self.show_page(name))
            nav.pack_start(button, False, False, 0)

        self.discover = self.page_box()
        self.discover.pack_start(self.heading("Discover Linux apps"), False, False, 0)
        self.discover_status = Gtk.Label(label="Loading apps from Luma Store…", xalign=0)
        self.discover.pack_start(self.discover_status, False, False, 0)
        self.discover_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.discover.pack_start(self.discover_list, True, True, 0)

        search_page = self.page_box()
        search_page.pack_start(self.heading("Search"), False, False, 0)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.connect("activate", self.search_apps)
        search_page.pack_start(self.search_entry, False, False, 0)
        self.search_status = Gtk.Label(label="Search Linux apps from the API.", xalign=0)
        search_page.pack_start(self.search_status, False, False, 0)
        self.search_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        search_page.pack_start(self.search_list, True, True, 0)

        self.categories_page = self.page_box()
        self.categories_page.pack_start(self.heading("Categories"), False, False, 0)
        self.categories_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.categories_page.pack_start(self.categories_box, False, False, 0)

        self.details_scrolled = Gtk.ScrolledWindow()
        self.details_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.details_content = self.page_box()
        self.details_scrolled.add(self.details_content)

        back = Gtk.Button(label="← Back")
        back.set_halign(Gtk.Align.START)
        back.connect("clicked", lambda _b: self.show_page("discover"))
        self.details_content.pack_start(back, False, False, 0)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.details_icon = Gtk.Image()
        self.details_icon.set_size_request(64, 64)
        header_box.pack_start(self.details_icon, False, False, 0)

        header_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.details_title = self.heading("App")
        self.details_summary = Gtk.Label(xalign=0, wrap=True)
        header_text.pack_start(self.details_title, False, False, 0)
        header_text.pack_start(self.details_summary, False, False, 0)
        header_box.pack_start(header_text, True, True, 0)
        self.details_content.pack_start(header_box, False, False, 0)

        self.details_meta = Gtk.Label(xalign=0, wrap=True)
        self.details_download = Gtk.Label(xalign=0, selectable=True, wrap=True)
        self.install_button = Gtk.Button(label="Install")
        self.install_button.set_halign(Gtk.Align.START)
        self.install_button.get_style_context().add_class("suggested-action")
        self.install_button.connect("clicked", self.install_current_app)
        self.install_status = Gtk.Label(xalign=0, wrap=True)

        self.extra_fields_label = self.heading("Additional API Information")
        self.extra_fields_label.set_margin_top(12)
        self.extra_fields_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self.screenshots_label = self.heading("Screenshots")
        self.screenshots_label.set_margin_top(12)
        self.screenshots_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.screenshots_scrolled = Gtk.ScrolledWindow()
        self.screenshots_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.screenshots_scrolled.set_min_content_height(200)
        self.screenshots_scrolled.add(self.screenshots_box)

        self.details_content.pack_start(self.details_meta, False, False, 0)
        self.details_content.pack_start(self.details_download, False, False, 0)
        self.details_content.pack_start(self.install_button, False, False, 0)
        self.details_content.pack_start(self.install_status, False, False, 0)
        self.details_content.pack_start(self.extra_fields_label, False, False, 0)
        self.details_content.pack_start(self.extra_fields_box, False, False, 0)
        self.details_content.pack_start(self.screenshots_label, False, False, 0)
        self.details_content.pack_start(self.screenshots_scrolled, False, False, 0)

        self.stack.add_named(self.discover, "discover")
        self.stack.add_named(search_page, "search")
        self.stack.add_named(self.categories_page, "categories")
        self.stack.add_named(self.details_scrolled, "details")
        self.stack.set_visible_child_name("discover")

        css = Gtk.CssProvider()
        css.load_from_data(b".page-title { font-size: 24px; font-weight: bold; } .app-name { font-size: 16px; font-weight: bold; }")
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.load_apps()

    @staticmethod
    def page_box():
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(24)
        return box

    @staticmethod
    def heading(text):
        label = Gtk.Label(label=text, xalign=0)
        label.get_style_context().add_class("page-title")
        return label

    def show_page(self, name):
        self.stack.set_visible_child_name(name)

    @staticmethod
    def clear(container):
        for child in container.get_children():
            container.remove(child)

    def app_row(self, app):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        box.set_border_width(12)

        icon_image = Gtk.Image()
        icon_image.set_size_request(48, 48)
        box.pack_start(icon_image, False, False, 0)
        icon_url = app.get("icon") or app.get("icon_url")
        if icon_url:
            self._set_image_from_url(icon_image, icon_url, 48, 48)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        name = Gtk.Label(label=app.get("name") or "Unnamed app", xalign=0)
        name.get_style_context().add_class("app-name")
        summary = Gtk.Label(label=app.get("summary") or app.get("description") or "", xalign=0, ellipsize=3)
        text.pack_start(name, False, False, 0)
        text.pack_start(summary, False, False, 0)
        view = Gtk.Button(label="View")
        view.connect("clicked", self.open_details, app)
        box.pack_start(text, True, True, 0)
        box.pack_end(view, False, False, 0)
        row.add(box)
        return row

    def load_apps(self):
        self.discover_status.set_text("Loading Linux apps from API…")
        threading.Thread(target=self._load_apps_worker, daemon=True).start()

    def _load_apps_worker(self):
        try:
            apps = LumaApi.apps()
            GLib.idle_add(self._apps_loaded, apps)
        except Exception as error:
            GLib.idle_add(self.discover_status.set_text, f"Could not load apps: {error}")

    def _apps_loaded(self, apps):
        self.apps = apps if isinstance(apps, list) else []
        self.clear(self.discover_list)
        for app in self.apps:
            self.discover_list.add(self.app_row(app))
        self.discover_status.set_text(f"{len(self.apps)} Linux app(s) available.")
        self.discover_list.show_all()
        self.rebuild_categories()
        return False

    def search_apps(self, _entry):
        query = self.search_entry.get_text().strip()
        self.clear(self.search_list)
        if not query:
            self.search_status.set_text("Enter a search term.")
            return
        self.search_status.set_text("Searching API…")
        threading.Thread(target=self._search_worker, args=(query,), daemon=True).start()

    def _search_worker(self, query):
        try:
            apps = LumaApi.apps(search=query)
            GLib.idle_add(self._search_loaded, apps)
        except Exception as error:
            GLib.idle_add(self.search_status.set_text, f"Search failed: {error}")

    def _search_loaded(self, apps):
        apps = apps if isinstance(apps, list) else []
        self.clear(self.search_list)
        for app in apps:
            self.search_list.add(self.app_row(app))
        self.search_status.set_text(f"{len(apps)} result(s).")
        self.search_list.show_all()
        return False

    def rebuild_categories(self):
        self.clear(self.categories_box)
        categories = sorted({str(app.get("category")) for app in self.apps if app.get("category")})
        if not categories:
            self.categories_box.pack_start(Gtk.Label(label="No categories returned by the API.", xalign=0), False, False, 0)
        for category in categories:
            button = Gtk.Button(label=category)
            button.connect("clicked", self.show_category, category)
            self.categories_box.pack_start(button, False, False, 0)
        self.categories_box.show_all()

    def reset_and_show_discover(self):
        self.clear(self.discover_list)
        for app in self.apps:
            self.discover_list.add(self.app_row(app))
        self.discover_status.set_text(f"{len(self.apps)} Linux app(s) available.")
        self.discover_list.show_all()
        self.show_page("discover")

    def show_category(self, _button, category):
        self.clear(self.discover_list)
        matching = [app for app in self.apps if str(app.get("category")) == category]
        for app in matching:
            self.discover_list.add(self.app_row(app))
        self.discover_status.set_text(f"{category}: {len(matching)} app(s)")
        self.discover_list.show_all()
        self.show_page("discover")

    def open_details(self, _button, app):
        app_id = app.get("id")
        if app_id is None:
            self.render_details(app)
            return
        self.details_title.set_text("Loading…")
        self.show_page("details")
        threading.Thread(target=self._details_worker, args=(app_id, app), daemon=True).start()

    def _details_worker(self, app_id, fallback):
        try:
            app = LumaApi.app(app_id)
        except Exception:
            app = fallback
        GLib.idle_add(self.render_details, app)

    def render_details(self, app):
        self.current_app = app
        self.details_title.set_text(app.get("name") or "App")
        self.details_summary.set_text(app.get("summary") or app.get("description") or "")

        # Icon
        self.details_icon.set_from_icon_name("system-run", Gtk.IconSize.DIALOG)
        icon_url = app.get("icon") or app.get("icon_url")
        if icon_url:
            self._set_image_from_url(self.details_icon, icon_url, 64, 64)

        # Screenshots
        self.clear(self.screenshots_box)
        screenshots = app.get("screenshots") or app.get("images") or []
        if isinstance(screenshots, str):
            screenshots = [s.strip() for s in screenshots.split(",") if s.strip()]

        if screenshots:
            self.screenshots_label.show()
            self.screenshots_scrolled.show()
            for screenshot_url in screenshots:
                img = Gtk.Image()
                img.set_margin_bottom(12)
                self.screenshots_box.pack_start(img, False, False, 0)
                self._set_image_from_url(img, screenshot_url, 320, 180)
        else:
            self.screenshots_label.hide()
            self.screenshots_scrolled.hide()

        category = app.get("category")
        if isinstance(category, dict):
            category = category.get("name")
        version = app.get("version") or app.get("version_name") or "Unknown"
        size = app.get("file_size_mb")
        package_format = app.get("package_format") or app.get("linux_package_base") or ""
        meta = f"Category: {category or 'Unknown'}  •  Version: {version}"
        if package_format:
            meta += f"  •  {package_format}"
        if size is not None:
            meta += f"  •  {size} MB"
        self.details_meta.set_text(meta)
        download_url = app.get("download_url") or ""
        self.details_download.set_text(f"Download: {download_url or 'No Linux download available'}")

        # Extra dynamic dynamic fields from API
        self.clear(self.extra_fields_box)
        known_keys = {"name", "summary", "description", "icon", "icon_url", "screenshots", "images", "category", "version", "version_name", "file_size_mb", "package_format", "linux_package_base", "download_url", "id"}
        extra_content_added = False
        for k, v in app.items():
            if k not in known_keys and v is not None and str(v).strip():
                extra_content_added = True
                lbl_key = k.replace("_", " ").title()
                field_label = Gtk.Label(xalign=0, selectable=True, wrap=True)
                field_label.set_markup(f"<b>{lbl_key}:</b> {v}")
                self.extra_fields_box.pack_start(field_label, False, False, 0)

        if extra_content_added:
            self.extra_fields_label.show()
            self.extra_fields_box.show()
        else:
            self.extra_fields_label.hide()
            self.extra_fields_box.hide()

        fmt = package_format.lower()
        url_lower = download_url.lower()
        is_appimage = fmt == "appimage" or ".appimage" in url_lower
        is_deb = fmt == "deb" or fmt == "debian" or ".deb" in url_lower
        is_rpm = fmt == "rpm" or ".rpm" in url_lower

        if is_appimage:
            self.install_button.set_label("Install AppImage")
            self.install_button.set_visible(True)
            self.install_button.set_sensitive(True)
            self.install_status.set_text("")
        elif is_deb:
            self.install_button.set_label("Install DEB Package")
            self.install_button.set_visible(True)
            self.install_button.set_sensitive(True)
            self.install_status.set_text("")
        elif is_rpm:
            self.install_button.set_label("Install RPM Package")
            self.install_button.set_visible(True)
            self.install_button.set_sensitive(True)
            self.install_status.set_text("")
        else:
            self.install_button.set_visible(False)
            self.install_status.set_text("No supported package format available for this app." if download_url else "No Linux download available.")

        self.show_page("details")
        return False

    def install_current_app(self, _button):
        app = self.current_app or {}
        url = app.get("download_url") or ""
        package_format = app.get("package_format") or app.get("linux_package_base") or ""

        fmt = package_format.lower()
        url_lower = url.lower()
        is_appimage = fmt == "appimage" or ".appimage" in url_lower
        is_deb = fmt == "deb" or fmt == "debian" or ".deb" in url_lower
        is_rpm = fmt == "rpm" or ".rpm" in url_lower

        if not (is_appimage or is_deb or is_rpm):
            self.install_status.set_text("Unsupported package format.")
            return

        self.install_button.set_sensitive(False)
        if is_appimage:
            self.install_status.set_text("Downloading AppImage…")
            threading.Thread(target=self._install_appimage_worker, args=(app, url), daemon=True).start()
        elif is_deb:
            self.install_status.set_text("Downloading DEB Package…")
            threading.Thread(target=self._install_native_package_worker, args=(app, url, "deb"), daemon=True).start()
        elif is_rpm:
            self.install_status.set_text("Downloading RPM Package…")
            threading.Thread(target=self._install_native_package_worker, args=(app, url, "rpm"), daemon=True).start()

    def _install_appimage_worker(self, app, url):
        try:
            target_dir = Path.home() / "Downloads"
            target_dir.mkdir(parents=True, exist_ok=True)
            parsed_name = Path(urllib.parse.urlparse(url).path).name
            safe_app_name = re.sub(r"[^A-Za-z0-9._-]+", "-", app.get("name") or "app").strip("-") or "app"
            filename = parsed_name if parsed_name.lower().endswith(".appimage") else f"{safe_app_name}.AppImage"
            destination = target_dir / filename
            temporary = destination.with_suffix(destination.suffix + ".part")
            request = urllib.request.Request(url, headers={"User-Agent": "Luma-Store-Linux/0.1"})
            with urllib.request.urlopen(request, timeout=60) as response, open(temporary, "wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            temporary.replace(destination)
            os.chmod(destination, 0o755)
            GLib.idle_add(self._install_finished, str(destination))
        except Exception as error:
            GLib.idle_add(self._install_failed, str(error))

    def _install_native_package_worker(self, app, url, pkg_type):
        try:
            target_dir = Path.home() / "Downloads"
            target_dir.mkdir(parents=True, exist_ok=True)
            parsed_name = Path(urllib.parse.urlparse(url).path).name
            safe_app_name = re.sub(r"[^A-Za-z0-9._-]+", "-", app.get("name") or "app").strip("-") or "app"
            ext = f".{pkg_type}"
            filename = parsed_name if parsed_name.lower().endswith(ext) else f"{safe_app_name}{ext}"
            destination = target_dir / filename
            temporary = destination.with_suffix(destination.suffix + ".part")
            request = urllib.request.Request(url, headers={"User-Agent": "Luma-Store-Linux/0.1"})
            with urllib.request.urlopen(request, timeout=60) as response, open(temporary, "wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            temporary.replace(destination)
            file_uri = destination.as_uri()
            GLib.idle_add(self._launch_package_installer, file_uri, str(destination), pkg_type)
        except Exception as error:
            GLib.idle_add(self._install_failed, str(error))

    def _launch_package_installer(self, file_uri, file_path, pkg_type):
        try:
            success = Gio.AppInfo.launch_default_for_uri(file_uri, None)
            if success:
                self.install_status.set_text(f"Downloaded package to {file_path} and opened the system installer.")
            else:
                self.install_status.set_text(f"Downloaded package to {file_path}. Please open it to complete the installation.")
        except Exception as error:
            self.install_status.set_text(f"Downloaded package to {file_path}, but could not open installer: {error}")
        self.install_button.set_label(f"Reinstall {pkg_type.upper()}")
        self.install_button.set_sensitive(True)
        return False

    def _install_finished(self, destination):
        self.install_status.set_text(f"Installed AppImage to {destination}")
        self.install_button.set_label("Reinstall AppImage")
        self.install_button.set_sensitive(True)
        return False

    def _install_failed(self, message):
        self.install_status.set_text(f"Installation failed: {message}")
        self.install_button.set_sensitive(True)
        return False

    def _set_image_from_url(self, gtk_image, url, width=None, height=None):
        def worker():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Luma-Store-Linux/0.1"})
                with urllib.request.urlopen(req, timeout=15) as response:
                    data = response.read()

                loader = GdkPixbuf.PixbufLoader()
                loader.write(data)
                loader.close()
                pixbuf = loader.get_pixbuf()

                if pixbuf and width and height:
                    pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)

                GLib.idle_add(gtk_image.set_from_pixbuf, pixbuf)
                GLib.idle_add(gtk_image.show)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()


class LumaStore(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.freetime.lumastore", flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        window = self.props.active_window or LumaStoreWindow(self)
        window.show_all()
        window.present()


if __name__ == "__main__":
    raise SystemExit(LumaStore().run(None))
