#include "mcp23016.h"
#include <wiringPiI2C.h>
#include <wiringPi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
//#define MCP_DEBUG

#define MAXIMUM_RETRIES 100
static unsigned char GP0VAL = 0x00;
static unsigned char GP1VAL = 0x00;
static int fd = 0;

static unsigned char MCP_writeRegister(unsigned char regNum, unsigned char value);
static unsigned char MCP_readRegister(unsigned char regNum);
static void MCP_updatePins(void);
static MCP_IOCHANGE state_change;

static void _iochange_isr(void)
{
    unsigned char pin_states[16];

    if (state_change)
    {
        MCP_readPins(0x01, pin_states);
        (state_change)(pin_states);
    }
}

void MCP_Init(unsigned char address, unsigned char fast, MCP_IOCHANGE statechange)
{
    GP0VAL = 0x00;
    GP1VAL = 0x00;

    //interrupt
    state_change = statechange;
    wiringPiSetupGpio();
    wiringPiISR(MCP_INT_PIN, INT_EDGE_FALLING, _iochange_isr);

    //i2c
    fd = wiringPiI2CSetup(address);

    if (fd < 0)
    {
        //problem
        printf("problem setting up I2C\n");
    }

    else
    {
        if (fast)
        {
            MCP_writeRegister(0x0A, 0x01);
        }
    }
}

static unsigned char MCP_writeRegister(unsigned char regNum, unsigned char value)
{
    unsigned int i;
    int result;

//    #ifdef MCP_DEBUG
//    printf("MCP: writing register %d, value is 0x%x\n", regNum, value);
//    #endif

    for (i = 0; i < MAXIMUM_RETRIES; i++)
    {
        result = wiringPiI2CWriteReg8(fd, regNum, value);
        if (result > -1)
        {
            break;
        }
    }

    if (i == MAXIMUM_RETRIES)
    {
        //error!
#ifdef MCP_DEBUG
        printf("MCP: error writing register %d\n", regNum);
#endif
        return 0x01;
    }

    return 0x00;
}

static unsigned char MCP_readRegister(unsigned char regNum)
{
    unsigned int i;
    int result;

    for (i = 0; i < MAXIMUM_RETRIES; i++)
    {
        result = wiringPiI2CReadReg8(fd, regNum);
        if (result > -1)
        {
            break;
        }
    }

    if (i == MAXIMUM_RETRIES)
    {
        //error!
#ifdef MCP_DEBUG
        printf("MCP: error reading register %d\n", regNum);
#endif
        return 0xff;
    }

//    #ifdef MCP_DEBUG
//    printf("MCP: read register %d, value is 0x%x\n", regNum, result);
//    #endif

    return result;
}

static void MCP_setInput(unsigned char pinNum)
{
    unsigned char current_value = 0x00;

    if ((pinNum < 8))
    {
        current_value = MCP_readRegister(0x06);
        current_value |= (1<<pinNum);
        MCP_writeRegister(0x06, current_value);
    }
    else
    {
        if (pinNum < 16)
        {
            current_value = MCP_readRegister(0x07);
            current_value |= (1<<(pinNum-8));
            MCP_writeRegister(0x07, current_value);
        }
    }
}

static void MCP_setOutput(unsigned char pinNum)
{
    unsigned char current_value = 0x00;

    if ((pinNum < 8))
    {
        current_value = MCP_readRegister(0x06);
        current_value &= ~(1<<pinNum);
        MCP_writeRegister(0x06, current_value);
    }
    else
    {
        if (pinNum < 16)
        {
            current_value = MCP_readRegister(0x07);
            current_value &= ~(1<<(pinNum-8));
            MCP_writeRegister(0x07, current_value);
        }
    }
}

void MCP_setDirection(unsigned char pinNum, unsigned char direction)
{
    if (direction == MCP_DIRECTION_IN)
    {
        #ifdef MCP_DEBUG
        printf("MCP: setting pin %d as input\n", pinNum);
        #endif
        MCP_setInput(pinNum);
    }
    else
    {
        #ifdef MCP_DEBUG
        printf("MCP: setting pin %d as output\n", pinNum);
        #endif
        MCP_setOutput(pinNum);
    }
}

static void MCP_updatePins(void)
{
    piLock(0);
    GP0VAL = MCP_readRegister(0x00);
    GP1VAL = MCP_readRegister(0x01);
    piUnlock(0);
}

unsigned char MCP_readPin(unsigned char pinNum, unsigned char refresh)
{
    if (refresh)
    {
        MCP_updatePins();
    }

    if ((pinNum < 8))
    {
        if (GP0VAL & (1<<pinNum))
        {
            return 0x01;
        }
        else
        {
            return 0x00;
        }
    }
    else
    {
        if ((pinNum > 7) && (pinNum < 16))
        {
            if (GP1VAL & (1<<(pinNum - 8)))
            {
                return 0x01;
            }
            else
            {
                return 0x00;
            }
        }
    }

    return 0x00;
}

#if 0
PyObject * MCP_PybyteToBoolVector(unsigned char byte)
{
    unsigned int i = 0;
    PyObject* result = PyList_New(0);

    for (i = 0; i < 8; i++)
    {
        if (byte & (1<<i))
        {
            PyList_Append(result, PyBool_FromLong(0x01));
        }
        else
        {
            PyList_Append(result, PyBool_FromLong(0x00));
        }
    }

    return result;
}
#endif

void MCP_byteToBoolVector(unsigned char byte, unsigned char * result)
{
    unsigned int i = 0;

    for (i = 0; i < 8; i++)
    {
        if (byte & (1<<i))
        {
            result[i] = 0x01;
        }
        else
        {
            result[i] = 0x00;
        }
    }
}

#if 0
PyObject * MCP_PyreadPins(unsigned char refresh)
{
    PyObject* result, *result1;
    unsigned int i = 0;

    if (refresh)
    {
        Py_BEGIN_ALLOW_THREADS
        MCP_updatePins();
        Py_END_ALLOW_THREADS
    }

    result = MCP_byteToBoolVector(GP0VAL);
    result1 = MCP_byteToBoolVector(GP1VAL);

    for (i = 0; i < 8; i++)
    {
        PyList_Append(result, PyList_GetItem(result1, i));
    }

    PyObject_Free(result1);

    return result;
}
#endif

void  MCP_readPins(unsigned char refresh, unsigned char* result)
{
    if (refresh)
    {
        MCP_updatePins();
    }

    MCP_byteToBoolVector(GP0VAL, result);
    MCP_byteToBoolVector(GP1VAL, result+8);
}

void MCP_writePin(unsigned char pinNum, unsigned char value)
{
    unsigned char current_value = 0x00;
    piLock(0);
    if ((pinNum < 8))
    {
        current_value = MCP_readRegister(0x00);
        if (value)
        {
            current_value |= (1<<pinNum);
        }
        else
        {
            current_value &= ~(1<<pinNum);
        }
        MCP_writeRegister(0x00, current_value);
    }
    else
    {
        if ((pinNum > 7) &&(pinNum < 16))
        {
            current_value = MCP_readRegister(0x01);
            if (value)
            {
                current_value |= (1<<(pinNum-8));
            }
            else
            {
                current_value &= ~(1<<(pinNum-8));
            }
            MCP_writeRegister(0x01, current_value);
        }
    }
    piUnlock(0);
}

void MCP_writePins(unsigned char * pinValues)
{
    unsigned char curr_gp0 = 0x00, curr_gp1 = 0x00;
    unsigned int i = 0;

    //update values
    MCP_updatePins();

    curr_gp0 = GP0VAL;
    curr_gp1 = GP1VAL;

    for (i = 0; i < 8; i++)
    {
        if (pinValues[i] == MCP_STATE_HIGH)
        {
            curr_gp0 |= (1<<i);
        }
        else
        {
            if (pinValues[i] == MCP_STATE_LOW)
            {
                curr_gp0 &= ~(1<<i);
            }
        }
    }

    for (i = 8; i < 16; i++)
    {
        if (pinValues[i] == MCP_STATE_HIGH)
        {
            curr_gp1 |= (1<<(i-8));
        }
        else
        {
            if (pinValues[i] == MCP_STATE_LOW)
            {
                curr_gp1 &= ~(1<<(i-8));
            }
        }
    }

    piLock(0);
    MCP_writeRegister(0x00, curr_gp0);
    MCP_writeRegister(0x01, curr_gp1);
    piUnlock(0);

}
