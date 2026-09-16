#include <gtk/gtk.h>

typedef struct {
    const gchar *name;
    const gchar *summary;
    const gchar *category;
    const gchar *version;
} LumaApp;

static const LumaApp apps[] = {
    {"GeoWeather", "A simple weather app for Android, Windows and Linux.", "Weather", "2.3.0"},
    {"SuperSMP Companion", "Companion app for the SuperSMP community.", "Games", "1.0"},
    {"Programming Language Clicker", "A clicker game about programming languages.", "Games", "1.0.3"},
    {"Luma Store", "The Freetime Maker app store.", "System", "0.1.0"},
};

static GtkWidget *stack;
static GtkWidget *details_title;
static GtkWidget *details_summary;
static GtkWidget *details_meta;

static void show_page(GtkButton *button, gpointer page_name) {
    (void)button;
    gtk_stack_set_visible_child_name(GTK_STACK(stack), (const gchar *)page_name);
}

static void show_details(GtkButton *button, gpointer data) {
    (void)button;
    const LumaApp *app = data;

    gchar *meta = g_strdup_printf("Category: %s  •  Version: %s", app->category, app->version);
    gtk_label_set_text(GTK_LABEL(details_title), app->name);
    gtk_label_set_text(GTK_LABEL(details_summary), app->summary);
    gtk_label_set_text(GTK_LABEL(details_meta), meta);
    g_free(meta);

    gtk_stack_set_visible_child_name(GTK_STACK(stack), "details");
}

static GtkWidget *make_app_row(const LumaApp *app) {
    GtkWidget *row = gtk_list_box_row_new();
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 16);
    GtkWidget *text = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    GtkWidget *name = gtk_label_new(app->name);
    GtkWidget *summary = gtk_label_new(app->summary);
    GtkWidget *button = gtk_button_new_with_label("View");

    gtk_widget_set_margin_start(box, 16);
    gtk_widget_set_margin_end(box, 16);
    gtk_widget_set_margin_top(box, 12);
    gtk_widget_set_margin_bottom(box, 12);

    gtk_label_set_xalign(GTK_LABEL(name), 0.0f);
    gtk_label_set_xalign(GTK_LABEL(summary), 0.0f);
    gtk_label_set_ellipsize(GTK_LABEL(summary), PANGO_ELLIPSIZE_END);
    gtk_style_context_add_class(gtk_widget_get_style_context(name), "app-name");

    gtk_widget_set_hexpand(text, TRUE);
    gtk_box_pack_start(GTK_BOX(text), name, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(text), summary, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(box), text, TRUE, TRUE, 0);
    gtk_box_pack_end(GTK_BOX(box), button, FALSE, FALSE, 0);
    gtk_container_add(GTK_CONTAINER(row), box);

    g_signal_connect(button, "clicked", G_CALLBACK(show_details), (gpointer)app);
    return row;
}

static GtkWidget *make_discover_page(void) {
    GtkWidget *outer = gtk_box_new(GTK_ORIENTATION_VERTICAL, 18);
    GtkWidget *title = gtk_label_new("Discover Linux apps");
    GtkWidget *subtitle = gtk_label_new("Browse apps available in Luma Store.");
    GtkWidget *list = gtk_list_box_new();

    gtk_widget_set_margin_start(outer, 24);
    gtk_widget_set_margin_end(outer, 24);
    gtk_widget_set_margin_top(outer, 24);
    gtk_widget_set_margin_bottom(outer, 24);

    gtk_label_set_xalign(GTK_LABEL(title), 0.0f);
    gtk_label_set_xalign(GTK_LABEL(subtitle), 0.0f);
    gtk_style_context_add_class(gtk_widget_get_style_context(title), "page-title");
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(list), GTK_SELECTION_NONE);

    gtk_box_pack_start(GTK_BOX(outer), title, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(outer), subtitle, FALSE, FALSE, 0);

    for (guint i = 0; i < G_N_ELEMENTS(apps); i++) {
        gtk_container_add(GTK_CONTAINER(list), make_app_row(&apps[i]));
    }

    gtk_box_pack_start(GTK_BOX(outer), list, TRUE, TRUE, 0);
    return outer;
}

static GtkWidget *make_search_page(void) {
    GtkWidget *outer = gtk_box_new(GTK_ORIENTATION_VERTICAL, 14);
    GtkWidget *title = gtk_label_new("Search");
    GtkWidget *entry = gtk_search_entry_new();
    GtkWidget *hint = gtk_label_new("Search support is ready for connection to the Luma Store backend.");

    gtk_widget_set_margin_start(outer, 24);
    gtk_widget_set_margin_end(outer, 24);
    gtk_widget_set_margin_top(outer, 24);
    gtk_widget_set_margin_bottom(outer, 24);
    gtk_label_set_xalign(GTK_LABEL(title), 0.0f);
    gtk_label_set_xalign(GTK_LABEL(hint), 0.0f);
    gtk_style_context_add_class(gtk_widget_get_style_context(title), "page-title");

    gtk_box_pack_start(GTK_BOX(outer), title, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(outer), entry, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(outer), hint, FALSE, FALSE, 0);
    return outer;
}

static GtkWidget *make_categories_page(void) {
    GtkWidget *outer = gtk_box_new(GTK_ORIENTATION_VERTICAL, 14);
    GtkWidget *title = gtk_label_new("Categories");
    const gchar *categories[] = {"Games", "Weather", "System", "Utilities", "Development"};

    gtk_widget_set_margin_start(outer, 24);
    gtk_widget_set_margin_end(outer, 24);
    gtk_widget_set_margin_top(outer, 24);
    gtk_widget_set_margin_bottom(outer, 24);
    gtk_label_set_xalign(GTK_LABEL(title), 0.0f);
    gtk_style_context_add_class(gtk_widget_get_style_context(title), "page-title");
    gtk_box_pack_start(GTK_BOX(outer), title, FALSE, FALSE, 0);

    for (guint i = 0; i < G_N_ELEMENTS(categories); i++) {
        GtkWidget *button = gtk_button_new_with_label(categories[i]);
        gtk_widget_set_halign(button, GTK_ALIGN_FILL);
        gtk_box_pack_start(GTK_BOX(outer), button, FALSE, FALSE, 0);
    }
    return outer;
}

static GtkWidget *make_details_page(void) {
    GtkWidget *outer = gtk_box_new(GTK_ORIENTATION_VERTICAL, 16);
    GtkWidget *back = gtk_button_new_with_label("← Back to Discover");
    GtkWidget *install = gtk_button_new_with_label("Install");

    gtk_widget_set_margin_start(outer, 24);
    gtk_widget_set_margin_end(outer, 24);
    gtk_widget_set_margin_top(outer, 24);
    gtk_widget_set_margin_bottom(outer, 24);

    details_title = gtk_label_new("App");
    details_summary = gtk_label_new("");
    details_meta = gtk_label_new("");
    gtk_label_set_xalign(GTK_LABEL(details_title), 0.0f);
    gtk_label_set_xalign(GTK_LABEL(details_summary), 0.0f);
    gtk_label_set_xalign(GTK_LABEL(details_meta), 0.0f);
    gtk_label_set_line_wrap(GTK_LABEL(details_summary), TRUE);
    gtk_style_context_add_class(gtk_widget_get_style_context(details_title), "page-title");
    gtk_widget_set_halign(back, GTK_ALIGN_START);
    gtk_widget_set_halign(install, GTK_ALIGN_START);
    gtk_style_context_add_class(gtk_widget_get_style_context(install), "suggested-action");

    g_signal_connect(back, "clicked", G_CALLBACK(show_page), "discover");

    gtk_box_pack_start(GTK_BOX(outer), back, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(outer), details_title, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(outer), details_summary, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(outer), details_meta, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(outer), install, FALSE, FALSE, 0);
    return outer;
}

static void activate(GtkApplication *app, gpointer user_data) {
    (void)user_data;
    GtkWidget *window = gtk_application_window_new(app);
    GtkWidget *root = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    GtkWidget *header = gtk_header_bar_new();
    GtkWidget *nav = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    GtkWidget *discover = gtk_button_new_with_label("Discover");
    GtkWidget *search = gtk_button_new_with_label("Search");
    GtkWidget *categories = gtk_button_new_with_label("Categories");

    gtk_window_set_title(GTK_WINDOW(window), "Luma Store");
    gtk_window_set_default_size(GTK_WINDOW(window), 960, 680);
    gtk_header_bar_set_title(GTK_HEADER_BAR(header), "Luma Store");
    gtk_header_bar_set_subtitle(GTK_HEADER_BAR(header), "Apps for Linux");
    gtk_header_bar_set_show_close_button(GTK_HEADER_BAR(header), TRUE);
    gtk_window_set_titlebar(GTK_WINDOW(window), header);

    gtk_box_pack_start(GTK_BOX(nav), discover, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(nav), search, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(nav), categories, FALSE, FALSE, 0);
    gtk_widget_set_margin_start(nav, 12);
    gtk_widget_set_margin_end(nav, 12);
    gtk_widget_set_margin_top(nav, 8);
    gtk_widget_set_margin_bottom(nav, 8);

    stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(stack), GTK_STACK_TRANSITION_TYPE_SLIDE_LEFT_RIGHT);
    gtk_stack_set_transition_duration(GTK_STACK(stack), 180);
    gtk_stack_add_named(GTK_STACK(stack), make_discover_page(), "discover");
    gtk_stack_add_named(GTK_STACK(stack), make_search_page(), "search");
    gtk_stack_add_named(GTK_STACK(stack), make_categories_page(), "categories");
    gtk_stack_add_named(GTK_STACK(stack), make_details_page(), "details");
    gtk_stack_set_visible_child_name(GTK_STACK(stack), "discover");

    g_signal_connect(discover, "clicked", G_CALLBACK(show_page), "discover");
    g_signal_connect(search, "clicked", G_CALLBACK(show_page), "search");
    g_signal_connect(categories, "clicked", G_CALLBACK(show_page), "categories");

    gtk_box_pack_start(GTK_BOX(root), nav, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(root), stack, TRUE, TRUE, 0);
    gtk_container_add(GTK_CONTAINER(window), root);

    GtkCssProvider *provider = gtk_css_provider_new();
    gtk_css_provider_load_from_data(provider,
        ".page-title { font-size: 24px; font-weight: bold; }"
        ".app-name { font-size: 16px; font-weight: bold; }"
        "list row { border-bottom: 1px solid alpha(currentColor, 0.12); }",
        -1, NULL);
    gtk_style_context_add_provider_for_screen(gdk_screen_get_default(),
        GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);

    gtk_widget_show_all(window);
}

int main(int argc, char **argv) {
    GtkApplication *app = gtk_application_new("com.freetime.LumaStore", G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(app, "activate", G_CALLBACK(activate), NULL);
    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);
    return status;
}
