
install_deps:
	test -d .venv || virtualenv .venv  --no-site-packages
	. .venv/bin/activate; pip install -e ".[dev]"

test_only:
	. .venv/bin/activate; pytest -v -s

test: install_deps test_only
