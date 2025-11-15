.NOTPARALLEL:
all: pre-commit test docs

docs:
	- cd docs && make html

pre-commit:
	- pre-commit run -a

test:
	- pytest -q -m "not no_xdist"
	- pytest -qn0 -m "no_xdist"
