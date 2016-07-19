//
// Low level access function to the LCD
//




// LCD Control constants
//#define FNT_PIN   18   // Font select
//#define REV_PIN   23  // Reverse
//#define CD_PIN   24  //  Command_\Data
//#define CE_PIN_PIN   25  //   \Chip_Enable

//#define FNT   1<<FNT_PIN
//#define REV   1<<REV_PIN
//#define CD   1<<CD_PIN
//#define CE_PIN   1<<CE_PIN_PIN
  
#include <unistd.h>
#include "gpio.h" 
//#include "lcd_register.h"

// LCD Control constants
#define FNT_PIN  18   // Font select
#define REV_PIN  23  // Reverse
#define CD_PIN   24  //  Command_\Data
#define CE_PIN   25  //   \Chip_Enable

//#define FNT   1<<FNT_PIN
//#define REV   1<<REV_PIN
//#define CD   1<<CD_PIN
//#define CE_PIN   1<<CE_PIN_PIN

//direct I/O control
#define D0_PIN 8
#define D1_PIN 7
#define D2_PIN 12
#define D3_PIN 16
#define D4_PIN 20
#define D5_PIN 21
#define D6_PIN 26
#define D7_PIN 19

//#define D0 1<<D0_PIN
//#define D1 1<<D1_PIN
//#define D2 1<<D2_PIN
//#define D3 1<<D3_PIN
//#define D4 1<<D4_PIN
//#define D5 1<<D5_PIN
//#define D6 1<<D6_PIN
//#define D7 1<<D7_PIN

#define _PUT_DATA(dat, mask, gpio) ((dat) & (mask) ? gpio_set((gpio)) : gpio_clr((gpio)))

//
// Set up the LCD
//
void LCD_setup()
{
    //reg_setup();
  // Set useful GPIO pins to output
  gpio_output_pin(REV_PIN);
  gpio_output_pin(FNT_PIN);
  gpio_output_pin(CD_PIN);
  gpio_output_pin(CE_PIN);

  //data pins
  gpio_output_pin(D0_PIN);
  gpio_output_pin(D1_PIN);
  gpio_output_pin(D2_PIN);
  gpio_output_pin(D3_PIN);
  gpio_output_pin(D4_PIN);
  gpio_output_pin(D5_PIN);
  gpio_output_pin(D6_PIN);
  gpio_output_pin(D7_PIN);
  
  gpio_set( CE_PIN );
}

void _put_data(short data)
{
    _PUT_DATA(data, 0x01, D0_PIN);
    _PUT_DATA(data, 0x02, D1_PIN);
    _PUT_DATA(data, 0x04, D2_PIN);
    _PUT_DATA(data, 0x08, D3_PIN);
    _PUT_DATA(data, 0x10, D4_PIN);
    _PUT_DATA(data, 0x20, D5_PIN);
    _PUT_DATA(data, 0x40, D6_PIN);
    _PUT_DATA(data, 0x80, D7_PIN);
}

void LCD_command(short command) {
  _put_data(command);
  gpio_set( CD_PIN );;

  gpio_clr( CE_PIN );
  usleep(1); // ! Important
  gpio_set( CE_PIN );
}

void LCD_data(short data) {
  _put_data(data);
  gpio_clr( CD_PIN );

  gpio_clr( CE_PIN );
  usleep(1); // ! Important
  gpio_set( CE_PIN );
}

void LCD_command_1D(short command, short data) {
  LCD_data(data);
  LCD_command(command);
}

void LCD_command_2D(short command, int data) {
  LCD_data(data & 0xFF);
  LCD_data((data >> 8) & 0xFF);
  LCD_command(command);
}

void LCD_Reverse(short rev) {
  if (rev) {
    gpio_clr( REV_PIN );
	} else {
    gpio_set( REV_PIN );
	}
}

void LCD_FontSelect(short high) {
  if (high) {
    gpio_clr( FNT_PIN );
	} else {
    gpio_set( FNT_PIN );
	}
}

