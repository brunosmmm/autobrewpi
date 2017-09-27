TARGET = ab_user
LIBS = -lm -lpthread -lzmq -lwiringPi
CC = gcc
CFLAGS = -Wall
CFLAGS_TARGET=

.PHONY: default all clean

default: $(TARGET)
all: default

OBJECTS = $(patsubst %.c, %.o, $(wildcard *.c))
HEADERS = $(wildcard *.h)

%.o: %.c $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $@

.PRECIOUS: $(TARGET) $(OBJECTS)

$(TARGET): $(OBJECTS)
	$(CC) $(LIBS) $(CFLAGS_TARGET) -o $@ $(OBJECTS)

clean:
	-rm -f *.o
	-rm -f $(TARGET)
