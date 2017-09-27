#ifndef MCP23016_H
#define MCP23016_H

#include <python3.5m/Python.h>

#define MCP_DIRECTION_IN 0x00
#define MCP_DIRECTION_OUT 0x01

#define MCP_STATE_LOW 0x00
#define MCP_STATE_HIGH 0x01
#define MCP_STATE_NONE 0x02

#define MCP_INT_PIN 4

typedef void (*MCP_IOCHANGE)(unsigned char*);

void MCP_setDirection(unsigned char pinNum, unsigned char direction);
void MCP_readPins(unsigned char refresh, unsigned char * result);
unsigned char MCP_readPin(unsigned char pinNum, unsigned char refresh);
void MCP_writePin(unsigned char pinNum, unsigned char value);
void MCP_writePins(unsigned char * pinValues);

void MCP_Init(unsigned char address, unsigned char fast, MCP_IOCHANGE statechange);


#endif /* MCP23016_H */
