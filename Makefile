
# Add dependencies to setup file and call this command to sync with Pipefile
install_deps:
	pipenv shell || true
	rm -f Pipfile.lock
	pipenv install '-e .'
	pipenv install --dev '-e .[dev]'

release:
	./tag_n_push.sh 0.0.1

test:
	pytest