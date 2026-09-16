.PHONY: install uninstall deb rpm

package = store_0.1.0_amd64

install:
	mkdir -p /usr/share/icons/hicolor/256x256/apps
	cp store.png /usr/share/icons/hicolor/256x256/apps/
	cp store.desktop /usr/share/applications/
	cp store.py /usr/local/bin/store
	chmod +x /usr/local/bin/store

uninstall:
	rm /usr/local/bin/store
	rm -rf /opt/store
	rm /usr/share/icons/hicolor/256x256/apps/store.png
	rm /usr/share/applications/store.desktop

deb:
	mkdir -p $(package)/usr/local/bin/
	mkdir -p $(package)/usr/share/icons/hicolor/256x256/apps/
	mkdir -p $(package)/usr/share/applications/
	cp store.py $(package)/usr/local/bin/store
	chmod +x $(package)/usr/local/bin/store
	cp store.png $(package)/usr/share/icons/hicolor/256x256/apps/
	cp store.desktop $(package)/usr/share/applications/
	dpkg-deb --build --root-owner-group $(package)

rpm:
	mkdir -p rpmbuild/SOURCES
	cp store.py xmrig store.png store.desktop rpmbuild/SOURCES/
	rpmbuild -bb --define "_topdir $(shell pwd)/rpmbuild" store.spec
	cp rpmbuild/RPMS/x86_64/*.rpm .
	rm -rf rpmbuild
