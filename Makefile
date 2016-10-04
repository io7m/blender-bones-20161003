all: calcium.zip

calcium.zip: __init__.py export.py
	zip -9 calcium.zip __init__.py export.py

clean:
	rm -f calcium.zip
