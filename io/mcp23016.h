#ifndef MCP23016_H
#define MCP23016_H

#include <python2.7/Python.h>

#define MCP_DIRECTION_IN 0x00
#define MCP_DIRECTION_OUT 0x01

#define MCP_STATE_LOW 0x00
#define MCP_STATE_HIGH 0x01
#define MCP_STATE_NONE 0x02

void MCP_setDirection(unsigned char pinNum, unsigned char direction);
void MCP_readPins(unsigned char refresh, unsigned char * result);
unsigned char MCP_readPin(unsigned char pinNum, unsigned char refresh);
void MCP_writePin(unsigned char pinNum, unsigned char value);
void MCP_writePins(unsigned char * pinValues);

void MCP_Init(unsigned char address, unsigned char fast);


#endif /* MCP23016_H */
