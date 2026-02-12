from asciimatics.effects import Print
from asciimatics.renderers import FigletText, StaticRenderer
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.event import KeyboardEvent
import sys

# We use a global or a dictionary to store the key outside the function
last_key = {"char": None}
if "-debug" in sys.argv:
    dtxt = "DEBUG MODE IS ON"
else: dtxt = ""


###     Print(screen, 
###         FigletText("ENGLISH", font='slant'), 
###         screen.height // 3 - 1),

def demo(screen):
    effects = [
        Print(screen, 
              FigletText("Coalide", font='slant'), 
              screen.height // 2 - 3),
        
              
        Print(screen, 
              StaticRenderer(images=["Press any key to start"]), 
              screen.height // 2 + 4),

        Print(screen, 
              StaticRenderer(images=[dtxt]), 
              screen.height // 2 + 6,
              colour=Screen.COLOUR_RED,
              attr=Screen.A_BOLD) # Added Bold to make it pop
    ]

    def check_input(event):
        if isinstance(event, KeyboardEvent):
            # event.key_code is the integer value of the key
            # We convert it to a character (like 'a', 'b', ' ')
            try:
                last_key["char"] = chr(event.key_code)
            except ValueError:
                last_key["char"] = "Special Key"
                
            raise StopIteration

    screen.play([Scene(effects, -1)], 
                stop_on_resize=True, 
                repeat=False, 
                unhandled_input=check_input)


def main(debug=False):
    try:
        Screen.wrapper(demo)
    except StopIteration:pass
    if last_key["char"] == "-":
        return "admin"
    else: return "play" 
    

if __name__ == "__main__":
    # This runs as soon as you hit ANY key
    if "--debug" in sys.argv:
        main(debug=True)
    else: main()
    print("\n" * 2)
    print("--- Game Started! ---")

    
    