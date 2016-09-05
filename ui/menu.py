from ui.frame import Frame
from ui.radiobutton import RadioButton, RadioGroup
from ui.label import Label, ValueCaption
from ui.element import Coordinate


class MenuItemError(Exception):
    pass


class MenuError(Exception):
    pass


class MenuItem(object):
    def __init__(self, item_id, item_caption, item_action=None,
                 value_getter=None, value_setter=None,
                 value_type=None, **kwargs):
        self._id = item_id
        self._caption = item_caption
        self._action = item_action
        self.getter = value_getter
        self.setter = value_setter
        self.value_type = value_type
        self._kwargs = kwargs
        self._parent = None
        self.selector = None
        self.label = None

    def do_action(self):
        if self._action == 'call':
            if 'callback' in self._kwargs:
                if self._kwargs['callback'] is not None:
                    self._kwargs['callback'](self._id)
        elif self._action == 'edit':
            if self._parent is not None:
                self._parent.edit_value()

    def get_item_id(self):
        return self._id

    def get_caption(self):
        return self._caption

    def calculate_value(self, value):
        if self.value_type == int:
            total_value = 0
            for i in range(0, len(value)):
                total_value += (10**i)*value[i]

            return total_value
        elif self.value_type == float:
            total_value = 0.0
            for i in range(0, len(value)):
                fp_size = self._kwargs['fixp_size']
                if i < fp_size:

                    total_value += (1.0/(10**(fp_size - i)))*value[i]
                else:
                    total_value += (10**(i - fp_size))*value[i]

            return total_value

    def check_validity(self, value):
        if self.value_type in (int, float):
            if 'max_val' in self._kwargs:
                if value > self._kwargs['max_val']:
                    return False
            if 'min_val' in self._kwargs:
                if value < self._kwargs['min_val']:
                    return False

        return True


class Menu(Frame):
    def __init__(self, **kwargs):
        self._sel_radius = kwargs.pop('selector_radius')
        self._font = kwargs.pop('font')
        self._colnum = kwargs.pop('cols')
        if 'selector_spacing' in kwargs:
            self._sel_spacing = kwargs.pop('selector_spacing')
        else:
            self._sel_spacing = 2
        if 'value_format' in kwargs:
            self._value_format = kwargs.pop('value_format')
        else:
            self._value_format = '{}'
        font_size = Label.guess_font_size(self._font)

        if font_size is None:
            try:
                self._font_w = kwargs.pop('font_w')
                self._font_h = kwargs.pop('font_h')
            except KeyError:
                raise MenuError('could not guess font size '
                                'and missing arguments "font_w" '
                                'and/or "font_h"')
        else:
            self._font_w = font_size['w']
            self._font_h = font_size['h']

        super(Menu, self).__init__(**kwargs)

        self._items = []
        self._group = RadioGroup()

        # item placement position
        self._current_position = Coordinate(0, 0)

        # calculate maximum length, etc
        col_w = self.w/self._colnum
        self._col_max_len = (col_w -
                             2*self._sel_radius -
                             self._sel_spacing)/self._font_w
        self._max_item_count = self._colnum*(self.h/(2*self._sel_radius +
                                                     self._sel_spacing))

        self._item_value = None
        self._editing = False

    def add_item(self, item):
        if not isinstance(item, MenuItem):
            raise TypeError('not a MenuItem instance')

        if len(self._items) == self._max_item_count:
            raise MenuError('cannot add any more items')

        item._parent = self
        self._items.append(item)
        # create widgets
        item.selector = RadioButton(r=self._sel_radius,
                                    id=item.get_item_id(),
                                    group=self._group,
                                    **self._current_position)
        item.label = ValueCaption(font=self._font,
                                  caption=item.get_caption(),
                                  maximum_length=self._col_max_len-1,
                                  id=item.get_item_id()+'_label',
                                  **item.selector.northeast+(self._sel_radius, 0))

        self.add_element(item.selector)
        self.add_element(item.label)

        # calculate next position
        if item.selector.southwest.y + 2*self._sel_radius + self._sel_spacing >\
           self.h - 1:
            self._current_position.y = 0
            self._current_position.x += self.w/self._colnum
        else:
            self._current_position = item.selector.southwest+(0, self._sel_spacing)

    def add_items(self, items):
        for item in items:
            self.add_item(item)

    def delete_item(self, item_index):
        item = self._items[item_index]
        if item.selector is not None:
            self.remove_element(item.selector)
        if item.label is not None:
            self.remove_element(item.label)

        self._items.remove(item)

    def delete_items(self):
        while len(self._items) > 0:
            self.delete_item(0)

    def select_first(self):
        if self._editing:
            return
        self._group.select_first()

    def select_next(self):
        if self._editing:
            return
        self._group.select_next()

    def select_prev(self):
        if self._editing:
            return
        self._group.select_prev()

    def item_click(self):
        if self._editing:
            self.finish_edit()
            return
        selected = self._group.get_selected_index()
        if selected is not None:
            self._items[selected].do_action()

    def insert_value(self, value):
        if self._editing is False:
            return

        self._item_value.append(value)
        # provide visual feedback here
        selected = self._group.get_selected_index()
        item_value = self._items[selected].calculate_value(self._item_value)
        current_formatted_value = self._value_format.format(item_value)
        menu_item = self.uids[self._items[selected].get_item_id()+'_label']
        menu_item.set_value(current_formatted_value)

    def delete_value(self):
        if self._editing is False:
            return

        if len(self._item_value) > 0:
            self._item_value.pop()
        selected = self._group.get_selected_index()
        item_value = self._items[selected].calculate_value(self._item_value)
        current_formatted_value = self._value_format.format(item_value)
        menu_item = self.uids[self._items[selected].get_item_id()+'_label']
        menu_item.set_value(current_formatted_value)

    def edit_value(self):
        selected = self._group.get_selected_index()
        if selected is not None:
            if self._items[selected].getter is not None\
               and self._items[selected].setter is not None:
                self._item_value = []
                self._editing = True
                label = self.uids[self._items[selected].get_item_id()+'_label']
                label.set_inverted()

    def finish_edit(self):
        selected = self._group.get_selected_index()
        if selected is not None:
            if self._items[selected].setter is not None:
                value = self._items[selected].calculate_value(self._item_value)
                self._items[selected].setter(value)
            label = self.uids[self._items[selected].get_item_id()+'_label']
            label.set_normal()
        self._editing = False

    def cancel_edit(self):
        selected = self._group.get_selected_index()
        if selected is not None:
            label = self.uids[self._items[selected].get_item_id()+'_label']
            label.set_normal()
        self._editing = False

        # update values
        self.update_values()

    def is_editing(self):
        return self._editing

    def update_values(self):
        for item in self._items:
            if item.getter is not None:
                new_value = item.getter()
                label = self.uids[item.get_item_id()+'_label']
                label.set_value(self._value_format.format(new_value))
