# Luma Store Linux

Native GTK3 edition of **Luma Store** for Linux.

## Current features

- Native GTK3 interface
- Discover page with app cards
- App details page
- Search page shell
- Categories page
- Linux desktop entry
- Meson build system

## Build

### Debian / Ubuntu

```bash
sudo apt install build-essential meson ninja-build libgtk-3-dev
meson setup build
meson compile -C build
./build/luma-store
```

### Fedora

```bash
sudo dnf install gcc meson ninja-build gtk3-devel
meson setup build
meson compile -C build
./build/luma-store
```

### Arch Linux

```bash
sudo pacman -S base-devel meson ninja gtk3
meson setup build
meson compile -C build
./build/luma-store
```

## Install locally

```bash
meson setup build --prefix=/usr
meson compile -C build
sudo meson install -C build
```

## Next steps

The current UI is ready to be connected to the real Luma Store API/Supabase backend. Installation handling can then support Linux package formats such as Flatpak and AppImage.
