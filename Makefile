all:

test:
	python -m pytest test_combine.py -v

lint:
	black *.py
	flake8 *.py
