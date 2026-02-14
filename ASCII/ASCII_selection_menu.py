from asciimatics.widgets import Frame, Layout, Divider, Label
from asciimatics.renderers import FigletText
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.event import KeyboardEvent
from asciimatics.exceptions import StopApplication

class ModernMenu(Frame):
    def __init__(self, screen):
        # Fill the screen but hide the borders for a cleaner look
        super(ModernMenu, self).__init__(
            screen, screen.height, screen.width, has_border=False, name="Main Menu"
        )
        self.set_theme("bright")
        self.result = None

        # 1. Header Layout
        header_layout = Layout([100])
        self.add_layout(header_layout)
        
        header = FigletText("COALIDE", font="standard")
        header_layout.add_widget(Label(header, height=header.max_height))
        header_layout.add_widget(Divider())

        # 2. Options Layout (Centered)
        # Using [1, 4, 1] gives the text plenty of breathing room
        options_layout = Layout([1, 4, 1])
        self.add_layout(options_layout)

        options_layout.add_widget(Label(""), 1) # Space
        options_layout.add_widget(Label("[ S ]  START GAME", align="<"), 1)
        options_layout.add_widget(Label("[ A ]  ADMIN PANEL", align="<"), 1)
        options_layout.add_widget(Label("[ Q ]  QUIT", align="<"), 1)
        
        # 3. Footer
        footer_layout = Layout([100])
        self.add_layout(footer_layout)
        footer_layout.add_widget(Divider())
        footer_layout.add_widget(Label("Press the corresponding key to select", align="^"))

        self.fix()

    def process_event(self, event):
        # This is our "Keyboard Listener"
        if isinstance(event, KeyboardEvent):
            key = chr(event.key_code).lower()
            if key == 's':
                self.result = 1
                raise StopApplication("Start")
            elif key == 'a':
                self.result = 2
                raise StopApplication("Admin")
            elif key == 'q':
                self.result = 3
                raise StopApplication("Exit")
        
        # If they press something else, let the frame handle it
        return super(ModernMenu, self).process_event(event)

def run_menu(screen):
    menu = ModernMenu(screen)
    screen.play([Scene([menu], -1)], stop_on_resize=True)
    return menu.result


def main():
    choice = Screen.wrapper(run_menu)
    choice = choice if choice else 1 # Default to "Start Game" if something goes wrong

    if choice == 1: return "dstart"
    elif choice == 2: return "admin"
    elif choice == 3: return "exit"

if __name__ == "__main__":
    c_ = main()
    if c_ == "dstart": print("Starting Game...")
    elif c_ == "admin": print("Opening Admin Panel...")
    elif c_ == "exit": print("Exiting...")
    else: print("Unknown choice, defaulting to Start Game...")