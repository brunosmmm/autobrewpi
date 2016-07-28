from ui.screenbuf import ScreenBuffer
from ui.checkbox import CheckBox
from ui.label import Label
from ui.button import Button
from ui.radiobutton import RadioButton
from ui.screen import Screen
from ui.modal import Modal
from gadget.control import GadgetVariableSpace
from input.inputcli import ABInputClient
from vspace.hystctl import HystController
from vspace.constant import ConstantValue
from vspace.byteexp import ByteExp
from vspace.bytecomp import ByteComp
from user.mainscr import ABMainScreen
from user.builder import SystemBuilder
from time import sleep
from datetime import datetime
import signal
import logging

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

    signal.signal(signal.SIGTERM, _handle_signal)

    logging.basicConfig(level=logging.DEBUG,
                        filename='autobrew.log',
                        filemode='w',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    #logging
    logger = logging.getLogger('AutoBrew')

    logger.info('AutoBrew loading...')

    icli = ABInputClient()
    buf = ScreenBuffer(240, 64, icli)
    gvspace = GadgetVariableSpace(0xff0001)

    #build system
    sys = SystemBuilder(config_file='user/absystem.json', gadget_vspace=gvspace)
    #get information
    gvspace._debug_dump_port_list()

    main_screen = ABMainScreen()
    buf.add_screen('main', main_screen)

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
