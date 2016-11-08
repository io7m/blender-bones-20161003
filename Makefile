all: calcium.zip

calcium.zip: src/__init__.py src/export.py
	mkdir calcium
	cp src/*.py calcium
	zip -r -9 calcium.zip calcium

clean:
	rm -rf calcium
	rm -f calcium.zip
