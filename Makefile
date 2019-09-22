
install_deps:
	pip install -e .
	pip install -e .[dev]

test_only:
	pytest -v

test: install_deps test_only
