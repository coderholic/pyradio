MODULE=pyradio
SPHINXBUILD=sphinx-build
ALLSPHINXOPTS= -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .
BUILDDIR=_build

.PHONY: build
build:
	python3 setup.py build

.PHONY: install
install:
	devel/build_install_pyradio 3

.PHONY: uninstall
uninstall:
	devel/build_install_pyradio -u

.PHONY: clean
clean:
	sudo rm -rf build dist docs/_build
	sudo find . -name "*.pyc" -delete
	sudo find . -name "*.orig" -delete
	sudo find . -name "*.log" -delete
	sudo find . -name "*.1.gz" -delete

.PHONY: register
register:
	python setup.py register

.PHONY: upload
upload:
	python setup.py sdist upload || echo 'Upload already'

.PHONY: test
test: audit
	python setup.py test

.PHONY: audit
audit:
	pylama $(MODULE) -i E501

.PHONY: doc
doc: docs
	python setup.py build_sphinx --source-dir=docs/ --build-dir=docs/_build --all-files
	python setup.py upload_sphinx --upload-dir=docs/_build/html
