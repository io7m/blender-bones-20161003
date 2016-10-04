all: calcium.zip

calcium.zip: __init__.py export.py
	mkdir calcium
	cp *.py calcium
	zip -r -9 calcium.zip calcium

clean:
	rm -rf calcium
	rm -f calcium.zip
