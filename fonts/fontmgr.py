from cfparse import CFontParser
import json
import re

class FontManager(object):

    def __init__(self, config_file='fonts/fontcfg.json'):

        font_config = None
        self._fonts = {}
        try:
            with open(config_file, 'r') as f:
                font_config = json.load(f)

        except IOError as e:
            #print 'could not load font configuration file: {}'.format(e.message)
            raise

        if font_config is not None:
            #load fonts

            for font_name, font_desc in font_config['load_fonts'].iteritems():

                m = re.match(r'.*\.cfont$', font_desc['path'])
                font_data = None
                if m is not None:

                    #load
                    parser = None
                    try:
                        with open(font_desc['path'], 'r') as f:
                            parser = CFontParser(f.readlines(), int(font_desc['dsize']))
                    except IOError:
                        #ignore font, couldnt load
                        # todo: LOG
                        print 'could not load font: {}'.format(font_desc['path'])
                        continue

                    font_data = parser.get_font_array()
                else:
                    print 'regex test failed for {}'.format(font_desc['path'])

                if font_data is not None:
                    print 'loaded font {} (w:{}, h:{})'.format(font_name,
                                                               font_data.font_w,
                                                               font_data.font_h)
                    self._fonts[font_name] = font_data

    def get_font_char(self, font_name, char_idx):

        if font_name not in self._fonts:
            raise KeyError('invalid font: {}'.format(font_name))

        if char_idx > len(self._fonts[font_name].font_data):
            raise KeyError('invalid index: {}'.format(char_idx))

        return self._fonts[font_name].font_data[char_idx]

    def get_font_width(self, font_name):

        if font_name not in self._fonts:
            raise KeyError('invalid font: {}'.format(font_name))

        return self._fonts[font_name].font_w

    def get_font_height(self, font_name):

        if font_name not in self._fonts:
            raise KeyError('invalid font: {}'.format(font_name))

        return self._fonts[font_name].font_h