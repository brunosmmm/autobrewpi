import json
import os
import logging


class RecipeManager(object):

    def __init__(self, recipe_path):

        self.logger = logging.getLogger('AutoBrew.RecipeMgr')

        self.recipes = {}
        self.recipe_path = recipe_path
        # find recipe files
        self.find_recipes()

        self.logger.info('loaded {} recipes'.format(len(self.recipes)))

        self._active_recipe = None

    def find_recipes(self):
        file_list = []
        for f in os.listdir(self.recipe_path):
            if f.endswith('.json') and\
               not f.startswith('.'):
                file_list.append(f)

        for f in file_list:
            try:
                with open(os.path.join(self.recipe_path, f), 'r') as data:
                    recipe = json.load(data)
            except (IOError, ValueError) as e:
                self.logger.warning('couldnt load '
                                    'recipe file "{}": {}'.format(f,
                                                                  e.message))
                continue

            recipe_id = f.split('.')[0]
            self.recipes[recipe_id] = recipe

    def load_recipe(self, recipe_id):
        if recipe_id not in self.recipes:
            raise KeyError('invalid recipe id: {}'.format(recipe_id))
        self._active_recipe = recipe_id

    def get_loaded_recipe(self):
        return self._active_recipe

    def get_recipe_list(self):
        return self.recipes.keys()

    def get_recipe(self, recipe_id):
        return self.recipes[recipe_id]
