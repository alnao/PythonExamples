# see https://github.com/urwid/urwid e https://urwid.org/examples/index.html#graph-py
# pip install urwid
from __future__ import annotations
import urwid

def main():
    blank = urwid.Divider()
    text_header = "Welcome to the urwid-nao!  UP / DOWN / PAGE UP / PAGE DOWN scroll.  F12 to exits."
    listbox_content = [
        blank,
        urwid.Padding(urwid.Text("text_intro"), left=2, right=2, min_width=20),
        blank,
    ]
    header = urwid.AttrMap(urwid.Text(text_header), "header")
    listbox = urwid.ListBox(urwid.SimpleListWalker(listbox_content))
    scrollable = urwid.ScrollBar(
        listbox,
        trough_char=urwid.ScrollBar.Symbols.LITE_SHADE,
    )
    frame = urwid.Frame(urwid.AttrMap(scrollable, "body"), header=header)
    # use appropriate Screen class
    if urwid.display.web.is_web_request():
        screen = urwid.display.web.Screen()
    else:
        screen = urwid.display.raw.Screen()

    def unhandled(key: str | tuple[str, int, int, int]) -> None:
        if key == "f12":
            raise urwid.ExitMainLoop()
        
    palette = [
        ("body", "black", "light gray", "standout"),
        ("reverse", "light gray", "black"),
        ("header", "white", "dark red", "bold"),
    ]
    
    urwid.MainLoop(frame, palette, screen, unhandled_input=unhandled).run()


def setup():
    urwid.display.web.set_preferences("Urwid Tour")
    # try to handle short web requests quickly
    if urwid.display.web.handle_short_request():
        return
    main()
if __name__ == "__main__" or urwid.display.web.is_web_request():
    setup()