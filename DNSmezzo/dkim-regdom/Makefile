CC=gcc
CFLAGS=-Wall -Werror -Wextra -Wstrict-prototypes -Wmissing-prototypes -Wpointer-arith -Wreturn-type -Wcast-qual -Wswitch -Wshadow -Wcast-align -Wno-unused-parameter -Wchar-subscripts -Winline -Wnested-externs -Wredundant-decls
SOURCES=test-dkim-regdom.c dkim-regdom.c dkim-regdom.h tld-canon.h
BINARIES=dkim-regdom.o test-dkim-regdom.o
EXECUTABLE=test-dkim-regdom

all: $(BINARIES) $(EXECUTABLE)

clean:
	rm -f $(EXECUTABLE) *.o *.gch

$(EXECUTABLE): $(BINARIES)
	$(CC) $(CFLAGS) -o $@ $(BINARIES) $(LDFLAGS)

$(BINARIES): $(SOURCES)
	$(CC) $(CFLAGS) -c $(SOURCES)

