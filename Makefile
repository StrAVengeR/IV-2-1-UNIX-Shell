CC=gcc
CFLAGS=-O2 -Wall -Wextra -std=c11
all: osh
osh: src/osh.c
	$(CC) $(CFLAGS) -o osh src/osh.c
test: osh
	bash tests/run_tests.sh
clean:
	rm -f osh
