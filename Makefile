all: reader.c
	gcc -lnfc -O2 -o reader reader.c
clean:
	rm -f reader

.PHONY: clean	
