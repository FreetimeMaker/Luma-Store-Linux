Name:           store
Version:        1.0.1
Release:        1%{?dist}
Summary:        Luma Store Application
License:        GPLv3
BuildArch:      x86_64

Source0:        store.py
Source2:        store.png
Source3:        store.desktop

Requires:       python3

%description
The Linux Version of Luma Store.

%prep

%build

%install
mkdir -p %{buildroot}/usr/local/bin
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps
mkdir -p %{buildroot}/usr/share/applications

install -m 755 %{_sourcedir}/store.py %{buildroot}/usr/local/bin/store
install -m 644 %{_sourcedir}/store.png %{buildroot}/usr/share/icons/hicolor/256x256/apps/store.png
install -m 644 %{_sourcedir}/store.desktop %{buildroot}/usr/share/applications/store.desktop

%files
/usr/local/bin/store
/usr/share/icons/hicolor/256x256/apps/store.png
/usr/share/applications/store.desktop
