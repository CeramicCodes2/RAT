from asciimatics.widgets import Frame, ListBox, Layout, Divider, Text, \
    Button, TextBox, Widget
from asciimatics.screen import Canvas
from asciimatics.scene import Scene
from sys import exit
from asciimatics.event import KeyboardEvent
from asciimatics.screen import Screen
from asciimatics.parsers import AnsiTerminalParser, Parser
from asciimatics.exceptions import ResizeScreenError, NextScene, StopApplication
from RCA import TCP_MASTER
class ListView(Frame):
    def __init__(self, screen, model:TCP_MASTER):
        super(ListView, self).__init__(screen,
                                       screen.height,
                                       int(screen.width * 0.50),
                                       on_load=self._reload_logging,
                                       hover_focus=True,
                                       title="RAT SHELL",
                                       x=0# start at cero position
                                       )
        # Save off the model that accesses the contacts database.
        self._model = model
        # Create the form for displaying the list ozf contacts.
        #self._list_view = ListBox(
        #    Widget.FILL_FRAME,
        #    model.get_summary(), name="contacts", on_select=self._on_pick)
        self.logging = TextBox(Widget.FILL_FRAME,name='logging',readonly=True,as_string=True,line_wrap=True)
        self._model.stdout = lambda arg: self.displayValue(arg)
        self.set_theme(theme='green')
        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(self.logging)
        layout.add_widget(Divider())
        layout2 = Layout([1])
        self.add_layout(layout2)
        layout2.add_widget(Button("Quit", self._quit), 0)
        self._model.stdout('STARTING LOGGER'.center(int(screen.width * 0.50) - 1,'='))
        self.fix()
    def checkSucress(self):
        self._model.codec = {'HEADER':'0x16'}
    def checkErrors(self):
        self._model.codec = {'HEADER':'0x15'}
    def writeCommand(self):
        self._model.codec = {'HEADER':'0x11'}
        self._model.command = ''# Text.data for example
    def displayValue(self,arg:str):
        ''' this method will display in the logging widget the new data parsed ''' 
        self.logging.value += str(arg) + '\n'
    def _restartServer(self):
        self._model.restartServer()
    def _reload_logging(self):
        ''' this funcion will be used to reload and load the new information about the command executed in the victim client '''
        self._model.codec = {'HEADER':'0x15'}
        self.checkErrors()
        self._model.run()
        self.checkSucress()
        self._model.run()
        #self._model.codec = 
        #self.logging.value += 

    @staticmethod
    def _quit():
        raise StopApplication("User pressed quit")

class Terminal(Widget):
    def __init__(self, name:str, height,title:str):
        
        super(Terminal, self).__init__(name)
        self.title = title
        self._required_height = height
        self._canvas:Canvas = None
        self._cursor_x, self._cursor_y = 0, 0
        self._show_cursor = True
        self._map = {}
        self._current_colours = None
        self.value = None
        self._parser = AnsiTerminalParser()
        for k, v in [
            (Screen.KEY_LEFT, self.on_kleft),
            (Screen.KEY_RIGHT, self.on_kright),
            (Screen.KEY_UP, self.on_key_up),
            (Screen.KEY_DOWN, self.on_key_down),
            (Screen.KEY_PAGE_UP, "kpp"),
            (Screen.KEY_PAGE_DOWN, "knp"),
            (Screen.KEY_HOME, "khome"),
            (Screen.KEY_END,self.on_scape),
            (Screen.KEY_DELETE, self.on_delete),
            (Screen.KEY_BACK, self.on_back)
        ]:
            self._map[k] = v
        self._map[Screen.KEY_TAB] = "\t".encode()
    def on_key_up(self):
        if self._cursor_y != 0:
            self._cursor_y -= 1
    def on_key_down(self):
        if self._cursor_y != self._canvas.height:
            self._cursor_y += 1

    def on_scape(self):
        self._cursor_y += 1
    def on_kleft(self):
        self._cursor_x -= 1
    def on_kright(self):
        self._cursor_x += 1
    def on_delete(self):
        self._print_at(text=' ' * self._canvas.width,x=0,y=self._cursor_y) # obtenemos largo de lo que se escirbio
        self.prompit(start_y=self._cursor_y)
        self._cursor_x = 4# prompit start line
        #self._cursor_x = 0
    def on_back(self):
        #self._cursor_x -= 1
        self._print_at(text=' ', x=self._cursor_x-1, y=self._cursor_y)
        self._cursor_x -= 1
    def set_layout(self, x, y, offset, w, h):
        super(Terminal,self).set_layout(x, y, offset, w, h)
        self._canvas = Canvas(self._frame.canvas, h, w,x=x,y=y)
        
    def update(self,frame_no):
        ''' draw the component ''' 
        self._canvas.refresh()
        if frame_no % 10 < 5 and self._show_cursor:
            origin = self._canvas.origin
            x = self._cursor_x + origin[0]
            y = self._cursor_y + origin[1] - self._canvas.start_line
            details = self._canvas.get_from(self._cursor_x, self._cursor_y)
            if details:
                char, colour, attr, bg = details
                attr |= Screen.A_REVERSE
                self._frame.canvas.print_at(chr(char), x, y, colour, attr, bg)
    def _print_at(self, text, x, y):
        """
        Helper function to simplify use of the canvas.
        """
        self._canvas.print_at(
            text,
            x, y,
            colour=self._current_colours[0], attr=self._current_colours[1], bg=self._current_colours[2])
    def prompit(self,start_y):
        self._canvas.print_at(text='>>>', x=0, y=start_y)
    def reset(self):
        """
        Reset the widget to a blank screen.
        """
        self._canvas = Canvas(self._frame.canvas, self._h, self._w, x=self._x, y=self._y)
        self._cursor_x, self._cursor_y = 0, 0
        self._current_colours = (Screen.COLOUR_WHITE, Screen.A_NORMAL, Screen.COLOUR_BLACK)
        self._canvas.centre(text=self.title, y=0)
        #self._canvas.print_at(text='>>>', x=0, y=1)
        self.prompit(start_y=1)
        self._cursor_x = 4
        self._cursor_y = 1
    def required_height(self, offset, width):
        """
        Required height for the terminal.
        """
        return self._required_height

    @property
    def frame_update_count(self):
        """
        Frame update rate required.
        """
        # Force refresh for cursor.
        return 5

    @property
    def value(self):
        """
        Terminal value - not needed for demo.
        """
        return

    @value.setter
    def value(self, new_value):
        return
    def _add_stream(self, value):
        """
        Process any output from the TTY.
        """
        lines = value.split("\n")
        for i, line in enumerate(lines):
            self._parser.reset(line, self._current_colours)
            for offset, command, params in self._parser.parse():
                if command == Parser.DISPLAY_TEXT:
                    # Just display the text...  allowing for line wrapping.
                    if self._cursor_x + len(params) > self._w:
                        part_1 = params[:self._w - self._cursor_x]
                        part_2 = params[self._w - self._cursor_x:]
                        self._print_at(part_1, self._cursor_x, self._cursor_y)
                        self._print_at(part_2, 0, self._cursor_y + 1)
                        self._cursor_x = len(part_2)
                        self._cursor_y += 1
                        if self._cursor_y - self._canvas.start_line >= self._h:
                            self._canvas.scroll()
                    else:
                        self._print_at(params, self._cursor_x, self._cursor_y)
                        self._cursor_x += len(params)
                elif command == Parser.CHANGE_COLOURS:
                    # Change current text colours.
                    self._current_colours = params
                elif command == Parser.NEXT_TAB:
                    # Move to next tab stop - hard-coded to default of 8 characters.
                    self._cursor_x = (self._cursor_x // 8) * 8 + 8
                elif command == Parser.MOVE_RELATIVE:
                    # Move cursor relative to current position.
                    self._cursor_x += params[0]
                    self._cursor_y += params[1]
                    if self._cursor_y < self._canvas.start_line:
                        self._canvas.scroll(self._cursor_y - self._canvas.start_line)
                elif command == Parser.MOVE_ABSOLUTE:
                    # Move cursor relative to specified absolute position.
                    if params[0] is not None:
                        self._cursor_x = params[0]
                    if params[1] is not None:
                        self._cursor_y = params[1] + self._canvas.start_line
                elif command == Parser.DELETE_LINE:
                    # Delete some/all of the current line.
                    if params == 0:
                        self._print_at(" " * (self._w - self._cursor_x), self._cursor_x, self._cursor_y)
                    elif params == 1:
                        self._print_at(" " * self._cursor_x, 0, self._cursor_y)
                    elif params == 2:
                        self._print_at(" " * self._w, 0, self._cursor_y)
                elif command == Parser.DELETE_CHARS:
                    # Delete n characters under the cursor.
                    for x in range(self._cursor_x, self._w):
                        if x + params < self._w:
                            cell = self._canvas.get_from(x + params, self._cursor_y)
                        else:
                            cell = (ord(" "),
                                    self._current_colours[0],
                                    self._current_colours[1],
                                    self._current_colours[2])
                        self._canvas.print_at(
                            chr(cell[0]), x, self._cursor_y, colour=cell[1], attr=cell[2], bg=cell[3])
                elif command == Parser.SHOW_CURSOR:
                    # Show/hide the cursor.
                    self._show_cursor = params
                elif command == Parser.CLEAR_SCREEN:
                    # Clear the screen.
                    self._canvas.clear_buffer(
                        self._current_colours[0], self._current_colours[1], self._current_colours[2])
            # Move to next line, scrolling buffer as needed.
            if i != len(lines) - 1:
                self._cursor_x = 0
                self._cursor_y += 1
                if self._cursor_y - self._canvas.start_line >= self._h:
                    self._canvas.scroll() 

    def process_event(self, event):
        if self._cursor_y - self._canvas.start_line >= self._h:
            self._canvas.scroll()
        if isinstance(event, KeyboardEvent):
            if event.key_code > 0:
                #chr(event.key_code)
                if event.key_code == 13:
                    self.value = self._canvas.get_from(x=self._canvas.width, y=self._cursor_y)
                    # gets the data what will sended to the server
                    self._cursor_x = 4# start line prompit
                    self.on_scape()
                    self.prompit(start_y=self._cursor_y)
                
                else:
                    self._add_stream(chr(event.key_code))
                #self._cursor_x += 1
                #print(event.key_code)
                #self._print_at(text=chr(event.key_code), x=self._cursor_x, y=self._cursor_y)
                #self._cursor_x += 1
                #print(event.)
                return
            
            elif event.key_code in self._map:
                #self._cursor_y += 1
                self._map.get(event.key_code)()
                #self._print_at(text=self._map.get(event.key_code), x=self._cursor_x, y=self._cursor_y)
                return
        return event


class testFrame(Frame):
    def __init__(self, screen, model):
        super(testFrame,self).__init__(
            screen, 
            height=screen.height,
            width=int(screen.width * 0.50),
            x=int((screen.width * 0.50) + 0.5),
            y=0,
            hover_focus=True)
        self._model = model
        self.set_theme(theme='green')
        #cv = Canvas(screen=screen, height=30, width=30)
        layout = Layout([100],fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(Terminal('he',Widget.FILL_FRAME,title='NO DATA'))
        #cv.print_at(text='hello', x=20, y=20)
        #layout2 = Layout([1,1,1,1],fill_frame=True)
        #self.add_layout(layout2)
        #layout2.add_widget(Button('ho',on_click=lambda x: print('a'),label='nme',name='nme' ),0)
        
        self.fix()
    def _reload_logging(self):
        ''' this funcion will be used to reload and load the new information about the command executed in the victim client '''
        pass
    @staticmethod
    def _quit():
        raise StopApplication("User pressed quit")
model = TCP_MASTER(7777)
def main(screen, scene):
    scenes = [
        Scene([ListView(screen, model),testFrame(screen,model=model)], -1, name="Main"),
    ]
    screen.play(scenes, stop_on_resize=True, start_scene=scene, allow_int=True)


last_scene = None
while True:
    try:
        Screen.wrapper(main, catch_interrupt=True, arguments=[last_scene])
        exit(0)
    except ResizeScreenError as e:
        last_scene = e.scene