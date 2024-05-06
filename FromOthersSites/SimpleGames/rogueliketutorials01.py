"""
SEE https://rogueliketutorials.com/tutorials/tcod/v2/part-1/
    and https://github.com/TStand90/tcod_tutorial_v2/tree/2020/part-1

SEE https://rogueliketutorials.com/tutorials/tcod/v2/part-0/
requirements.txt
    tcod>=11.13
    numpy>=1.18
    "pip install -r requirements.txt" or  "apt-get install libsdl2-dev"
    pip install tcod

    download https://raw.githubusercontent.com/TStand90/tcod_tutorial_v2/1667c8995fb0d0fd6df98bd84c0be46cb8b78dac/dejavu10x10_gs_tc.png

"""

from typing import Optional
import tcod.event
import os
dirname=os.path.dirname(__file__)

class Action:
    pass
class EscapeAction(Action):
    pass
class MovementAction(Action):
    def __init__(self, dx: int, dy: int):
        super().__init__()
        self.dx = dx
        self.dy = dy
#from actions import Action, EscapeAction, MovementAction
class EventHandler(tcod.event.EventDispatch[Action]):
    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        action: Optional[Action] = None
        key = event.sym
        if key == tcod.event.K_UP:
            action = MovementAction(dx=0, dy=-1)
        elif key == tcod.event.K_DOWN:
            action = MovementAction(dx=0, dy=1)
        elif key == tcod.event.K_LEFT:
            action = MovementAction(dx=-1, dy=0)
        elif key == tcod.event.K_RIGHT:
            action = MovementAction(dx=1, dy=0)
        elif key == tcod.event.K_ESCAPE:
            action = EscapeAction()
        return action

import tcod
def main() -> None:
    screen_width = 80
    screen_height = 50
    player_x = int(screen_width / 2)
    player_y = int(screen_height / 2)

    tileset = tcod.tileset.load_tilesheet(
        dirname + "/rogueliketutorials01.png", 32, 8, tcod.tileset.CHARMAP_TCOD #ex dejavu10x10_gs_tc
    )
    event_handler = EventHandler()
    with tcod.context.new_terminal(
        screen_width,
        screen_height,
        tileset=tileset,
        title="Yet Another Roguelike Tutorial",
        vsync=True,
    ) as context:
        root_console = tcod.Console(screen_width, screen_height, order="F")
        while True:
            root_console.print(x=player_x, y=player_y, string="@") #root_console.print(x=1, y=1, string="@")
            context.present(root_console)
            root_console.clear()
            for event in tcod.event.wait():
#                if event.type == "QUIT":
#                    raise SystemExit()
               action = event_handler.dispatch(event)
               if action is None:
                   continue
               if isinstance(action, MovementAction):
                   player_x += action.dx
                   player_y += action.dy
               elif isinstance(action, EscapeAction):
                   raise SystemExit()

if __name__ == "__main__":
    main()


    