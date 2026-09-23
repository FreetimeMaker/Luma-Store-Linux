#!/usr/bin/env python3
import http.server
import json
import os
import re
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

import gi
from supabase import create_client
from supabase.client import ClientOptions

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf

API_BASE = "https://api.free-time.me/v2/lumastore"
PLATFORM = "linux"
APPIMAGE_DIR = Path.home() / ".local" / "bin" / "luma-store-appimages"

SUPABASE_URL = "https://ndlaevedujqxhygbyxfh.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_HlppI4ILiXV7DZkpyrDEhQ_ytb2vV6g"
SESSION_FILE = Path.home() / ".config" / "luma-store" / "session.json"


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


class FileSupabaseStorage:
    """Simple file-backed storage adapter for supabase-py sessions."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()

    def _read(self):
        try:
            if not self.path.exists():
                return {}
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data), encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        temporary.replace(self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def get_item(self, key):
        with self._lock:
            return self._read().get(key)

    def set_item(self, key, value):
        with self._lock:
            data = self._read()
            data[key] = value
            self._write(data)

    def remove_item(self, key):
        with self._lock:
            data = self._read()
            data.pop(key, None)
            if data:
                self._write(data)
            else:
                try:
                    self.path.unlink(missing_ok=True)
                except Exception:
                    pass


class NativeSupabaseAuth:
    """Native Supabase authentication backed by supabase-py."""

    def __init__(self):
        self.client = create_client(
            SUPABASE_URL,
            SUPABASE_PUBLISHABLE_KEY,
            options=ClientOptions(
                flow_type="pkce",
                persist_session=True,
                auto_refresh_token=True,
                storage=FileSupabaseStorage(SESSION_FILE),
            ),
        )

    @staticmethod
    def _as_dict(value):
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "dict"):
            return value.dict()
        return {
            key: getattr(value, key)
            for key in dir(value)
            if not key.startswith("_") and not callable(getattr(value, key, None))
        }

    def sign_out(self):
        try:
            self.client.auth.sign_out()
        finally:
            try:
                SESSION_FILE.unlink(missing_ok=True)
            except Exception:
                pass

    def session(self):
        try:
            return self.client.auth.get_session()
        except Exception:
            return None

    def access_token(self):
        session = self.session()
        return getattr(session, "access_token", None) if session else None

    def user(self):
        if not self.access_token():
            return None
        response = self.client.auth.get_user()
        return self._as_dict(getattr(response, "user", None))

    def provider(self):
        user = self.user() or {}
        metadata = user.get("app_metadata") or {}
        return metadata.get("provider") or "OAuth"

    def login(self, provider):
        result = {"code": None, "error": None}

        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                result["code"] = query.get("code", [None])[0]
                result["error"] = query.get("error_description", query.get("error", [None]))[0]
                ok = bool(result["code"]) and not result["error"]
                title = "Luma Store login complete" if ok else "Luma Store login failed"
                message = (
                    "You can close this tab and return to Luma Store."
                    if ok
                    else (result["error"] or "No authorization code was returned.")
                )
                html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:system-ui;background:#09111f;color:#eef2ff;display:grid;place-items:center;min-height:100vh;margin:0}}
main{{max-width:520px;padding:32px;border:1px solid #ffffff22;border-radius:28px;background:#ffffff10;box-shadow:0 20px 60px #0008}}
h1{{margin-top:0}}p{{color:#b9c3d5;line-height:1.6}}</style></head><body><main><h1>{title}</h1><p>{message}</p></main></body></html>"""
                payload = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, _format, *_args):
                return

        server = http.server.HTTPServer(("127.0.0.1", 8765), CallbackHandler)
        server.timeout = 180
        callback = f"http://127.0.0.1:{server.server_port}/auth/callback"

        options = {"redirect_to": callback}
        if provider == "github":
            options["scopes"] = "read:user public_repo"

        oauth = self.client.auth.sign_in_with_oauth({
            "provider": provider,
            "options": options,
        })
        auth_url = getattr(oauth, "url", None)
        if not auth_url:
            server.server_close()
            raise RuntimeError("Supabase did not return an OAuth URL.")

        if not webbrowser.open(str(auth_url)):
            server.server_close()
            raise RuntimeError("Could not open the system browser.")

        server.handle_request()
        server.server_close()

        if result["error"]:
            raise RuntimeError(result["error"])
        if not result["code"]:
            raise RuntimeError("Login timed out or no authorization code was returned.")

        return self.client.auth.exchange_code_for_session({
            "auth_code": result["code"],
        })


class DeveloperDashboardApi:
    def __init__(self, auth):
        self.auth = auth

    def submissions(self):
        user = self.auth.user()
        if not user or not user.get("id"):
            raise RuntimeError("Sign in to load your developer dashboard.")

        columns = (
            "id,name,short_description,description,status,submitted_at,status_updated_at,"
            "category,version,platform,linux_package_base,store_app_id,review_message,repo_url,"
            "download_url,package_name"
        )
        response = (
            self.auth.client.table("luma_submissions")
            .select(columns)
            .eq("user_id", user["id"])
            .order("submitted_at", desc=True)
            .execute()
        )
        return response.data or []


class LumaStoreWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Luma Store")
        self.set_default_size(960, 680)
        self.apps = []
        self.current_app = None
        self.auth = NativeSupabaseAuth()
        self.dashboard_api = DeveloperDashboardApi(self.auth)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None and screen.is_composited():
            self.set_visual(visual)
            self.set_app_paintable(True)

        header = Gtk.HeaderBar(title="Luma Store", subtitle="Native Linux client", show_close_button=True)
        header.get_style_context().add_class("glass-header")
        self.set_titlebar(header)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.get_style_context().add_class("app-root")
        self.add(root)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        nav.set_border_width(10)
        nav.get_style_context().add_class("glass-nav")
        root.pack_start(nav, False, False, 0)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT, transition_duration=180)
        root.pack_start(self.stack, True, True, 0)
        for label, page in (("Discover", "discover"), ("Search", "search"), ("Categories", "categories"), ("Dev Dashboard", "dashboard")):
            button = Gtk.Button(label=label)
            button.get_style_context().add_class("nav-button")
            if page == "discover":
                button.connect("clicked", lambda _b: self.reset_and_show_discover())
            elif page == "dashboard":
                button.connect("clicked", lambda _b: self.open_dashboard())
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

        self.dashboard = self.page_box()
        dashboard_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        dashboard_titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        dashboard_titles.pack_start(self.heading("Developer Dashboard"), False, False, 0)
        dashboard_subtitle = Gtk.Label(
            label="Manage and review your Luma Store submissions in a fully native GTK view.",
            xalign=0,
            wrap=True,
        )
        dashboard_subtitle.get_style_context().add_class("muted")
        dashboard_titles.pack_start(dashboard_subtitle, False, False, 0)
        dashboard_header.pack_start(dashboard_titles, True, True, 0)
        self.dashboard.pack_start(dashboard_header, False, False, 0)

        self.dashboard_auth_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.dashboard_auth_card.get_style_context().add_class("glass-card")
        self.dashboard_auth_card.set_border_width(16)
        self.dashboard_auth_status = Gtk.Label(label="Sign in to use the developer dashboard.", xalign=0, wrap=True)
        self.dashboard_auth_card.pack_start(self.dashboard_auth_status, False, False, 0)

        self.dashboard_login_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.github_login_button = Gtk.Button(label="Sign in with GitHub")
        self.gitlab_login_button = Gtk.Button(label="Sign in with GitLab")
        self.github_login_button.get_style_context().add_class("glass-primary")
        self.github_login_button.connect("clicked", self.start_dashboard_login, "github")
        self.gitlab_login_button.connect("clicked", self.start_dashboard_login, "gitlab")
        self.dashboard_login_buttons.pack_start(self.github_login_button, False, False, 0)
        self.dashboard_login_buttons.pack_start(self.gitlab_login_button, False, False, 0)
        self.dashboard_auth_card.pack_start(self.dashboard_login_buttons, False, False, 0)

        self.dashboard_session_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        refresh_button = Gtk.Button(label="Refresh")
        refresh_button.connect("clicked", lambda _b: self.load_dashboard_submissions())
        logout_button = Gtk.Button(label="Sign out")
        logout_button.connect("clicked", self.dashboard_sign_out)
        self.dashboard_session_actions.pack_start(refresh_button, False, False, 0)
        self.dashboard_session_actions.pack_start(logout_button, False, False, 0)
        self.dashboard_auth_card.pack_start(self.dashboard_session_actions, False, False, 0)
        self.dashboard.pack_start(self.dashboard_auth_card, False, False, 0)

        self.dashboard_stats = Gtk.Label(label="No dashboard data loaded yet.", xalign=0, wrap=True)
        self.dashboard_stats.get_style_context().add_class("dashboard-stats")
        self.dashboard.pack_start(self.dashboard_stats, False, False, 0)

        submissions_title = Gtk.Label(label="My submissions", xalign=0)
        submissions_title.get_style_context().add_class("section-title")
        self.dashboard.pack_start(submissions_title, False, False, 0)
        self.dashboard_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.dashboard_list.get_style_context().add_class("transparent-list")
        self.dashboard_scrolled = Gtk.ScrolledWindow()
        self.dashboard_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.dashboard_scrolled.add(self.dashboard_list)
        self.dashboard.pack_start(self.dashboard_scrolled, True, True, 0)

        self.details_scrolled = Gtk.ScrolledWindow()
        self.details_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.details_content = self.page_box()
        self.details_scrolled.add(self.details_content)

        back = Gtk.Button(label="← Back")
        back.set_halign(Gtk.Align.START)
        back.connect("clicked", lambda _b: self.show_page("discover"))
        self.details_content.pack_start(back, False, False, 0)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        header_box.get_style_context().add_class("glass-card")
        header_box.set_border_width(14)
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
        self.stack.add_named(self.dashboard, "dashboard")
        self.stack.add_named(self.details_scrolled, "details")
        self.stack.set_visible_child_name("discover")

        css = Gtk.CssProvider()
        css.load_from_data(b"""
            window, .app-root {
                background-color: rgba(8, 14, 26, 0.97);
                color: #eef2ff;
            }
            headerbar.glass-header {
                background-image: linear-gradient(to bottom, rgba(31, 41, 67, 0.88), rgba(17, 24, 39, 0.82));
                border-bottom: 1px solid rgba(255, 255, 255, 0.11);
                box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
                color: #f8fafc;
            }
            .glass-nav {
                margin: 2px 14px 8px 14px;
                padding: 6px;
                border-radius: 22px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.10), rgba(99, 102, 241, 0.08));
                box-shadow: 0 12px 34px rgba(0, 0, 0, 0.24);
            }
            button {
                min-height: 34px;
                padding: 7px 13px;
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.10);
                background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.10), rgba(255, 255, 255, 0.04));
                color: #e5e7eb;
                box-shadow: 0 7px 18px rgba(0, 0, 0, 0.17);
            }
            button:hover {
                background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.16), rgba(99, 102, 241, 0.12));
                border-color: rgba(165, 180, 252, 0.42);
            }
            button:active {
                background-color: rgba(99, 102, 241, 0.24);
            }
            button.nav-button {
                min-height: 36px;
                border-radius: 16px;
                box-shadow: none;
            }
            button.glass-primary, button.suggested-action {
                background-image: linear-gradient(135deg, rgba(99, 102, 241, 0.92), rgba(139, 92, 246, 0.84));
                border-color: rgba(199, 210, 254, 0.45);
                color: white;
            }
            entry, searchentry {
                min-height: 38px;
                padding: 6px 12px;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                background-color: rgba(15, 23, 42, 0.70);
                color: #f8fafc;
            }
            .page-surface {
                background-color: rgba(8, 14, 26, 0.50);
            }
            .glass-card, .dashboard-stats {
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.11);
                background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.085), rgba(99, 102, 241, 0.055));
                box-shadow: 0 14px 34px rgba(0, 0, 0, 0.22);
            }
            .dashboard-stats {
                padding: 12px 14px;
                color: #cbd5e1;
            }
            list, listbox, .transparent-list {
                background-color: transparent;
            }
            listbox row {
                margin: 5px 0;
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 0.09);
                background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.075), rgba(255, 255, 255, 0.025));
            }
            listbox row:hover {
                border-color: rgba(165, 180, 252, 0.30);
                background-color: rgba(99, 102, 241, 0.09);
            }
            scrolledwindow {
                border: none;
                background-color: transparent;
            }
            .page-title {
                font-size: 26px;
                font-weight: 700;
                color: #f8fafc;
            }
            .section-title {
                font-size: 18px;
                font-weight: 700;
                color: #f8fafc;
                margin-top: 5px;
            }
            .app-name {
                font-size: 16px;
                font-weight: 700;
                color: #f8fafc;
            }
            .muted {
                color: #aab4c5;
            }
            .status-approved { color: #86efac; }
            .status-rejected { color: #fca5a5; }
            .status-pending { color: #fde68a; }
            .status-review { color: #c4b5fd; }
        """)
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.load_apps()

    @staticmethod
    def page_box():
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(24)
        box.get_style_context().add_class("page-surface")
        return box

    @staticmethod
    def heading(text):
        label = Gtk.Label(label=text, xalign=0)
        label.get_style_context().add_class("page-title")
        return label

    def show_page(self, name):
        self.stack.set_visible_child_name(name)

    def open_dashboard(self):
        self.show_page("dashboard")
        self.refresh_dashboard_state()
        if self.auth.access_token():
            self.load_dashboard_submissions()

    def refresh_dashboard_state(self):
        token = self.auth.access_token()
        if not token:
            self.dashboard_auth_status.set_text(
                "Sign in with GitHub or GitLab. Authentication opens in your system browser; the dashboard itself stays native."
            )
            self.dashboard_login_buttons.show()
            self.dashboard_session_actions.hide()
            self.dashboard_stats.set_text("Sign in to load your submissions.")
            self.clear(self.dashboard_list)
            self.dashboard_list.show_all()
            return

        try:
            user = self.auth.user() or {}
            metadata = user.get("user_metadata") or {}
            display_name = (
                metadata.get("user_name")
                or metadata.get("preferred_username")
                or metadata.get("full_name")
                or user.get("email")
                or "Developer"
            )
            provider = self.auth.provider()
            self.dashboard_auth_status.set_text(f"Signed in as {display_name} via {provider.title()}.")
            self.dashboard_login_buttons.hide()
            self.dashboard_session_actions.show()
        except Exception as error:
            self.dashboard_auth_status.set_text(f"Session error: {error}")
            self.dashboard_login_buttons.show()
            self.dashboard_session_actions.hide()

    def start_dashboard_login(self, _button, provider):
        self.dashboard_auth_status.set_text(
            f"Opening {provider.title()} in your system browser… Complete the login there and return to Luma Store."
        )
        self.github_login_button.set_sensitive(False)
        self.gitlab_login_button.set_sensitive(False)
        threading.Thread(target=self._dashboard_login_worker, args=(provider,), daemon=True).start()

    def _dashboard_login_worker(self, provider):
        try:
            self.auth.login(provider)
            GLib.idle_add(self._dashboard_login_done)
        except Exception as error:
            GLib.idle_add(self._dashboard_login_failed, str(error))

    def _dashboard_login_done(self):
        self.github_login_button.set_sensitive(True)
        self.gitlab_login_button.set_sensitive(True)
        self.refresh_dashboard_state()
        self.load_dashboard_submissions()
        return False

    def _dashboard_login_failed(self, message):
        self.github_login_button.set_sensitive(True)
        self.gitlab_login_button.set_sensitive(True)
        self.dashboard_auth_status.set_text(f"Login failed: {message}")
        return False

    def dashboard_sign_out(self, _button):
        self.auth.sign_out()
        self.refresh_dashboard_state()

    def load_dashboard_submissions(self):
        if not self.auth.access_token():
            self.refresh_dashboard_state()
            return
        self.dashboard_stats.set_text("Loading submissions…")
        threading.Thread(target=self._dashboard_submissions_worker, daemon=True).start()

    def _dashboard_submissions_worker(self):
        try:
            submissions = self.dashboard_api.submissions()
            GLib.idle_add(self._dashboard_submissions_loaded, submissions)
        except Exception as error:
            GLib.idle_add(self._dashboard_submissions_failed, str(error))

    def _dashboard_submissions_loaded(self, submissions):
        submissions = submissions if isinstance(submissions, list) else []
        self.clear(self.dashboard_list)
        counts = {}
        for submission in submissions:
            status = str(submission.get("status") or "Unknown")
            counts[status] = counts.get(status, 0) + 1
            self.dashboard_list.add(self.submission_row(submission))

        summary_order = ["Draft", "Pending", "In Review", "Changes Requested", "Approved", "Rejected", "Archived"]
        summary = "  •  ".join(f"{name}: {counts[name]}" for name in summary_order if counts.get(name))
        self.dashboard_stats.set_text(
            f"{len(submissions)} submission(s)" + (f"  —  {summary}" if summary else "")
        )
        if not submissions:
            empty = Gtk.Label(label="No submissions yet.", xalign=0)
            empty.set_border_width(14)
            empty.get_style_context().add_class("muted")
            self.dashboard_list.add(empty)
        self.dashboard_list.show_all()
        self.refresh_dashboard_state()
        return False

    def _dashboard_submissions_failed(self, message):
        self.dashboard_stats.set_text(f"Could not load dashboard: {message}")
        return False

    def submission_row(self, submission):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        box.set_border_width(13)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name = Gtk.Label(label=submission.get("name") or "Untitled submission", xalign=0)
        name.get_style_context().add_class("app-name")
        status_text = str(submission.get("status") or "Unknown")
        status = Gtk.Label(label=status_text, xalign=0)
        lowered = status_text.lower()
        if lowered == "approved":
            status.get_style_context().add_class("status-approved")
        elif lowered == "rejected":
            status.get_style_context().add_class("status-rejected")
        elif lowered in ("pending", "changes requested"):
            status.get_style_context().add_class("status-pending")
        elif lowered == "in review":
            status.get_style_context().add_class("status-review")
        title_line.pack_start(name, False, False, 0)
        title_line.pack_start(status, False, False, 0)
        text.pack_start(title_line, False, False, 0)

        description = submission.get("short_description") or submission.get("description") or ""
        if description:
            desc = Gtk.Label(label=str(description), xalign=0, ellipsize=3)
            desc.get_style_context().add_class("muted")
            text.pack_start(desc, False, False, 0)

        meta_bits = [
            str(value) for value in (
                submission.get("category"),
                submission.get("platform"),
                submission.get("version"),
            ) if value
        ]
        if meta_bits:
            meta = Gtk.Label(label="  •  ".join(meta_bits), xalign=0)
            meta.get_style_context().add_class("muted")
            text.pack_start(meta, False, False, 0)

        review_message = submission.get("review_message")
        if review_message:
            review = Gtk.Label(label=f"Review: {review_message}", xalign=0, wrap=True)
            review.get_style_context().add_class("status-pending")
            text.pack_start(review, False, False, 0)

        details = Gtk.Button(label="Details")
        details.connect("clicked", self.show_submission_details, submission)
        box.pack_start(text, True, True, 0)
        box.pack_end(details, False, False, 0)
        row.add(box)
        return row

    def show_submission_details(self, _button, submission):
        lines = []
        fields = [
            ("Status", "status"),
            ("Category", "category"),
            ("Platform", "platform"),
            ("Version", "version"),
            ("Package", "package_name"),
            ("Repository", "repo_url"),
            ("Download", "download_url"),
            ("Submitted", "submitted_at"),
            ("Updated", "status_updated_at"),
            ("Review message", "review_message"),
        ]
        for label, key in fields:
            value = submission.get(key)
            if value:
                lines.append(f"{label}: {value}")
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.CLOSE,
            text=submission.get("name") or "Submission details",
        )
        dialog.format_secondary_text("\n".join(lines) or "No additional information available.")
        dialog.run()
        dialog.destroy()


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
        is_deb = fmt == "deb" or fmt == "debian" or ".deb" in url_lower
        is_rpm = fmt == "rpm" or ".rpm" in url_lower

        if is_deb:
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
        is_deb = fmt == "deb" or fmt == "debian" or ".deb" in url_lower
        is_rpm = fmt == "rpm" or ".rpm" in url_lower

        if not (is_deb or is_rpm):
            self.install_status.set_text("Unsupported package format.")
            return

        self.install_button.set_sensitive(False)
        if is_deb:
            self.install_status.set_text("Downloading DEB Package…")
            threading.Thread(target=self._install_native_package_worker, args=(app, url, "deb"), daemon=True).start()
        elif is_rpm:
            self.install_status.set_text("Downloading RPM Package…")
            threading.Thread(target=self._install_native_package_worker, args=(app, url, "rpm"), daemon=True).start()


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
        self.install_status.set_text(f"Downloaded package to {destination}")
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
