from abpi.user.controllerscr import ABCtlScreen
from abpi.ui.menu import Menu, MenuItem
from abpi.ui.viewport import ViewPort


class ABRecipeScreen(ABCtlScreen):
    def __init__(self, **kwargs):
        kwargs['title'] = 'Receitas'
        kwargs['label_2s'] = 'Carrega'
        self._recipemgr = kwargs.pop('recipemgr')
        super(ABRecipeScreen, self).__init__(**kwargs)

        self._recipe_viewport = ViewPort(x=0,
                                         y=0,
                                         w=self._statframe.w,
                                         h=self._statframe.h,
                                         virtual_w=self._statframe.w,
                                         virtual_h=1000,
                                         visible=True)
        self._recipelist = Menu(x=0,
                                y=0,
                                selector_radius=5,
                                font='5x12',
                                cols=1,
                                w=self._recipe_viewport.virtual_w,
                                h=self._recipe_viewport.virtual_h)

        self._statframe.add_element(self._recipe_viewport)
        self._recipe_viewport.add_element(self._recipelist)

    def populate_recipe_list(self):
        recipe_list = self._recipemgr.get_recipe_list()

        self._recipelist.delete_items()
        menu_item_list = []
        for recipe_id in recipe_list:
            recipe = self._recipemgr.get_recipe(recipe_id)

            menu_item = MenuItem(recipe_id,
                                 recipe['title'],
                                 item_action='call',
                                 callback=self._enter_recipe)
            menu_item_list.append(menu_item)

        self._recipelist.add_items(menu_item_list)

    def _enter_recipe(self, recipe_id):
        self._recipemgr.load_recipe(recipe_id)
        recipe_abbrev = self._recipemgr.get_recipe(recipe_id)['abbrev']
        self._show_msg_modal('Receita "{}" carregada'.format(recipe_abbrev))

    def _screen_activated(self, **kwargs):
        super(ABRecipeScreen, self)._screen_activated(**kwargs)
        self._recipemgr.find_recipes()
        self.populate_recipe_list()
        self._recipelist.select_first()

    def _input_event(self, evt):

        super(ABRecipeScreen, self)._input_event(evt)

        if evt['event'] == 'switches.press':
            if evt['data'] == '3':
                self._parent.activate_screen('main')
            if evt['data'] == '1':
                self._recipelist.item_click()

        elif evt['event'] == 'encoder.cw':
            if self._current_frame == 'stat':
                self._recipelist.select_next()

        elif evt['event'] == 'encoder.ccw':
            if self._current_frame == 'stat':
                self._recipelist.select_prev()
