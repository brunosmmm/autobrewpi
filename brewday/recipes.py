import json
import os
import logging


class RecipeManager(object):

    def __init__(self, recipe_path):

        self.logger = logging.getLogger('AutoBrew.RecipeMgr')

        self.recipes = {}
        # find recipe files
        file_list = []
        for f in os.listdir(recipe_path):
            if f.endswith('*.json'):
                file_list.append(f)

        for f in file_list:
            try:
                with open(os.path.join(recipe_path, f), 'r') as data:
                    recipe = json.load(data)
            except IOError:
                self.logger.warning('couldnt load recipe file "{}"'.format(f))
                continue

            recipe_id = f.spli('.')[0]
            self.recipes[recipe_id] = recipe
            self.logger.debug('loaded recipe "{}"'.format(recipe['title']))

        self.logger.info('loaded {} recipes'.format(len(self.recipes)))
