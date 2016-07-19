TARGET = screen.so
LIBS = -lm
CC = gcc
CFLAGS = -fPIC -Wall

.PHONY: default all clean

default: $(TARGET)
all: default

OBJECTS = $(patsubst %.c, %.o, $(wildcard *.c))
HEADERS = $(wildcard *.h)

%.o: %.c $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $@

.PRECIOUS: $(TARGET) $(OBJECTS)

$(TARGET): $(OBJECTS)
	$(CC) -shared $(LIBS) -o $@ $(OBJECTS)

clean:
	-rm -f *.o
	-rm -f $(TARGET)
