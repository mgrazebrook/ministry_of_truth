'''Game main module.

Contains the entry point used by the run_game.py script.

Feel free to put all your game code here, or in other modules in this "gamelib"
package.
'''

# TODO: Make scene time manage pause and re-load

import os
from . import data
import pygame
import json
from collections import namedtuple
import pickle
import time


DISPLAY_SIZE = 1024, 650
FONT = "Sans" # Georgia
MAX_LINES = 7
BLOTTER_COLOURS = (
    (102, 204, 255),
    (255, 153, 204),
    (204, 255, 153),
    (153, 255, 204),
    (204, 153, 255),
    (255, 204, 153),
)

def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error as message:
        print( 'Cannot load image:', name )
        raise SystemExit(message)
    image = image.convert()
    if colorkey is not None:
        if colorkey is -1:
            colorkey = image.get_at((0,0))
        image.set_colorkey(colorkey, pygame.RLEACCEL)
    return image, image.get_rect()


class Progress:
    """
    The things which change in the model as the game progresses.
    """
    def __init__(self, current_game_map):
        self.game_time = 10
        self.wounded = False
        self.clues = set()
        self.set_game_map(current_game_map)

    def set_game_map(self, game_map):
        self.game_map = game_map
        self.scene_time = time.time()
        self.visible_things = []
        self.help = None
        self.visible_things = [ 
            thing 
            for thing in self.game_map.scene.things 
            if thing.show
        ]
        self.blotter = [
            (BLOTTER_COLOURS[0], line.format(hours_left = self.game_time))
            for line in game_map.scene.blotter
        ]
        self.stale = True
        self.game_time -= 1

    def update(self):
        pass # TODO: Enable/disable menu items




class Model:
    def __init__(self):
        self.game_map = GameMap("main.json")
        self.progress = Progress(self.game_map)
        self.blotter_colour_index = 0
        
    def update(self):
        self.progress.update()

    def get_image(self):
        return self.progress.game_map.image

    def get_level_name(self):
        return self.progress.game_map.scene.name
    
    def get_things(self):
        self.progress.visible_things

    def left_action(self, target, action):
        if action == "reset":
            self.progress = Progress(self.game_map)
        elif action[-5:] == ".json":
            self.progress.set_game_map(GameMap(action))
        elif action == "plot":
            try:
                for clue in target.clues:
                    if clue[0] == '-':
                        self.progress.clues.remove(clue[1:])
                    else:
                        self.progress.clues.add(clue)
                    self.progress.stale = True
            except AttributeError:
                pass # optional attribute
            
            try:
                self.blotter_colour_index = (self.blotter_colour_index + 1) % len(BLOTTER_COLOURS)
                self.progress.blotter += [
                    (BLOTTER_COLOURS[self.blotter_colour_index], line)
                    for line in target.result
                ]
                self.progress.blotter = self.progress.blotter[-MAX_LINES:]
            except AttributeError:
                pass # optional attribute

    def right_action(self, target, kind):
        """
        Help text
        """
        self.progress.help = target.help

    def clear(self):
        self.progress.help = None


class GameMap:
    all_game_maps = {}
    
    """
    Immutable, like a level
    """
    def __init__(self, scene_file):
        """
        :param level_name: name of the json file in the data folder.
        """
        if scene_file in self.all_game_maps:
            self.scene = self.all_game_maps[scene_file]
        else:
            self.scene = json.load(
                data.load(scene_file),
                object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))

        image_file = data.filepath(self.scene.image)
        self.image, self.image_rect = load_image(image_file) # TODO: Not in the model!


class MenuItem(pygame.sprite.Sprite):
    base_image = None
    base_rect = None
    font = None
    
    def __init__(self, model, button_spec, x, y):
        super().__init__()
        
        if MenuItem.base_image is None:
            MenuItem.base_image, MenuItem.base_rect = load_image("blue_button.png", (255,255,255))
            MenuItem.font = pygame.font.SysFont(FONT, 30)

        self.image = MenuItem.base_image.convert()
        self.rect = self.image.get_rect()
        self.model = model
        self.target = button_spec
        text = self.font.render(button_spec.label, True, (255, 0, 0))
        bx, by = self.rect.size
        tx, ty = text.get_rect().size
        pos = int((bx-tx)/2), int((by-ty)/2)
        self.image.blit(text, pos)
        self.rect.move_ip(x, y)


    def leftclick(self):
        self.model.left_action(self.target, self.target.action)


    def rightclick(self):
        self.model.right_action(self.target, "help")


class Menu(pygame.sprite.Group):
    def __init__(self, model, screen):
        super().__init__()

        self.screen = screen

        image_rect = model.get_image().get_rect()
        MARGIN=5
        self.rect = pygame.Rect(
            image_rect.right + MARGIN, 
            MARGIN, 
            DISPLAY_SIZE[0] - image_rect.right - MARGIN * 2, 
            image_rect.height - MARGIN)

        scene = model.progress.game_map.scene
        item_height = int(self.rect.height / 7) + MARGIN
        for i, button_spec in enumerate(scene.menu):
            if (hasattr(button_spec, "condition") 
                and not model.progress.clues.issuperset(button_spec.condition)):
                continue
            if (hasattr(button_spec, "block") 
                and not model.progress.clues.isdisjoint(button_spec.block)):
                continue
            x = self.rect.left 
            y = self.rect.top + i * item_height
            self.add(MenuItem(model, button_spec, x, y))


    def onclick(self, pos, left_click):
        """
        Test for collision and take appropriate action
        
        :param left_click: left if true, else right
        """
        for button in self:
            if button.rect.collidepoint(pos):
                if left_click:
                    button.leftclick()
                else:
                    button.rightclick()


    def update(self):
        # TODO: Disable items which aren't valid.
        # TODO: Maybe change colour if time sensitive
        pass


    def draw(self):
        self.screen.fill( (20,10,80), self.rect)
        super().draw(self.screen)


class MinistryOfTruth:
    save_file_name = "save/save.pickle"
    parchment = None
    parchment_rect = None
    parchment_font = None
    blotter_font = None

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(DISPLAY_SIZE)
        self.clock = pygame.time.Clock()
        self.sprites = pygame.sprite.Group()

        try:
            self.model = pickle.load(self.save_file_name)
        except:
            self.reset()
        self.menu = Menu(self.model, self.screen)

        if self.parchment is None:
            MinistryOfTruth.parchment, MinistryOfTruth.parchment_rect = load_image("old-parchment.jpg")
            MinistryOfTruth.parchment_font = pygame.font.SysFont(FONT, 20, italic=True)
            MinistryOfTruth.blotter_font = pygame.font.SysFont(FONT, 18)

    def reset(self):
        try:
            os.unlink(self.save_file_name)
        except FileNotFoundError:
            pass
        self.model = Model()
        
    def save(self):
        pickle.dump(self.model, self.save_file_name)

    def do_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.model.progress.help = None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.menu.onclick(event.pos, event.button==1)
        return True


    def update(self):
        self.model.update()
        self.menu.update()


    def draw(self):
        progress = self.model.progress

        if progress.stale:
            pygame.display.set_caption(self.model.get_level_name())
            progress.stale = False
            self.menu = Menu(self.model, self.screen)

        self.screen.fill((0,0,0))
        self.screen.blit(self.model.get_image(), (0,0))
        self.menu.draw()

        if progress.help:
            parchment_pos = (150,95)
            self.screen.blit(self.parchment, parchment_pos)
            for i, line in enumerate(progress.help):
                pos = parchment_pos[0] + 20, parchment_pos[1] + 40 + i * 20
                line_image = MinistryOfTruth.parchment_font.render(line, True, (0,26,102))
                self.screen.blit(line_image, pos)

        for i, (colour, line) in enumerate(self.model.progress.blotter):
            pos = 20, 510 + i * 18
            line_image = MinistryOfTruth.blotter_font.render(line, True, colour)
            self.screen.blit(line_image, pos)

        pygame.display.flip()


    def run(self):
        while self.do_events():
            self.update()
            self.draw()
            self.clock.tick(40)


def main():
    try:
        app = MinistryOfTruth()
        app.run()
    finally:
        pygame.quit()
