
install_deps:
	poetry install

test_only:
	poetry run pytest -v -s

test: install_deps test_only
