from ui.screenbuf import ScreenBuffer
from gadget.control import GadgetVariableSpace
from input.inputcli import ABInputClient
from user.mainscr import ABMainScreen
from user.mashctlscr import ABMashScreen
from user.boilctlscr import ABBoilScreen
from user.splashscr import ABSplashScreen
from user.builder import SystemBuilder
from time import sleep
from datetime import datetime
import signal
import logging
from brewday.recipes import RecipeManager

usleep = lambda x: sleep(x/1000000.0)

if __name__ == "__main__":

    def _handle_signal(*args):
        print "Exiting..."
        buf.stop()
        buf.join()
        gvspace.stop()
        gvspace.join()
        icli.stop()
        icli.join()
        exit(0)

    def shutdown():
        _handle_signal()

    signal.signal(signal.SIGTERM, _handle_signal)

    logging.basicConfig(level=logging.DEBUG,
                        filename='autobrew.log',
                        filemode='w',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    # logging
    logger = logging.getLogger('AutoBrew')

    logger.info('AutoBrew loading...')

    icli = ABInputClient()
    gvspace = GadgetVariableSpace(0xff000001)

    def _turn_lcd_on():
        gvspace.send_gadget_command(0x05)

    splash_screen = ABSplashScreen()
    buf = ScreenBuffer(240,
                       64,
                       icli,
                       screen_on_hook=_turn_lcd_on,
                       splash=splash_screen)

    # build system
    sys = SystemBuilder(config_file='config/user/absystem.json', gadget_vspace=gvspace)
    # get information
    gvspace._debug_dump_port_list()

    main_screen = ABMainScreen()
    mash_screen = ABMashScreen(varspace=gvspace)
    boil_screen = ABBoilScreen(varspace=gvspace)
    buf.add_screen('main', main_screen)
    buf.add_screen('mash', mash_screen)
    buf.add_screen('boil', boil_screen)

    #start threads
    buf.start()
    gvspace.start()
    icli.start()

    #activate screen
    buf.activate_screen('main')

    logger.info('AutoBrew started')
    last_cycle = datetime.now()
    while True:
        try:
            td = datetime.now() - last_cycle
            last_cycle = datetime.now()

            sleep(0.1)
        except KeyboardInterrupt:
            _handle_signal(None)
