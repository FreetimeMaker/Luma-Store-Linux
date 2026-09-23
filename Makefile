.PHONY: install uninstall deb rpm

package = store_1.0.1_amd64
runtime_requirements = runtime-requirements.txt
vendor_path = /usr/lib/luma-store/vendor

install:
	mkdir -p /usr/share/icons/hicolor/256x256/apps
	mkdir -p $(vendor_path)
	python3 -m pip install --disable-pip-version-check --no-compile --target $(vendor_path) -r $(runtime_requirements)
	cp store.png /usr/share/icons/hicolor/256x256/apps/
	cp store.desktop /usr/share/applications/
	cp store.py /usr/local/bin/store
	chmod +x /usr/local/bin/store

uninstall:
	rm -f /usr/local/bin/store
	rm -rf /usr/lib/luma-store
	rm -rf /opt/store
	rm -f /usr/share/icons/hicolor/256x256/apps/store.png
	rm -f /usr/share/applications/store.desktop

deb:
	rm -rf $(package)/usr/lib/luma-store/vendor
	mkdir -p $(package)/usr/local/bin/
	mkdir -p $(package)/usr/lib/luma-store/vendor/
	mkdir -p $(package)/usr/share/icons/hicolor/256x256/apps/
	mkdir -p $(package)/usr/share/applications/
	python3 -m pip install --disable-pip-version-check --no-compile --target $(package)/usr/lib/luma-store/vendor -r $(runtime_requirements)
	cp store.py $(package)/usr/local/bin/store
	chmod +x $(package)/usr/local/bin/store
	cp store.png $(package)/usr/share/icons/hicolor/256x256/apps/
	cp store.desktop $(package)/usr/share/applications/
	dpkg-deb --build --root-owner-group $(package)

rpm:
	rm -rf rpmbuild
	mkdir -p rpmbuild/SOURCES/luma-vendor
	python3 -m pip install --disable-pip-version-check --no-compile --target rpmbuild/SOURCES/luma-vendor -r $(runtime_requirements)
	tar -C rpmbuild/SOURCES -czf rpmbuild/SOURCES/luma-vendor.tar.gz luma-vendor
	cp store.py store.png store.desktop rpmbuild/SOURCES/
	rpmbuild -bb --define "_topdir $(shell pwd)/rpmbuild" store.spec
	cp rpmbuild/RPMS/x86_64/*.rpm .
	rm -rf rpmbuild
