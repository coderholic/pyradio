class Log(object):
    """ Log class that outputs text to a curses screen """

    msg = None
    cursesScreen = None

    def __init__(self):
        self.width = None

    def setScreen(self, cursesScreen):
        self.cursesScreen = cursesScreen
        self.width = cursesScreen.getmaxyx()[1] - 5

        # Redisplay the last message
        if self.msg:
            self.write(self.msg)

    def write(self, msg):
        self.msg = msg.strip()

        if self.cursesScreen:
            self.cursesScreen.erase()
            self.cursesScreen.addstr(0, 1, self.msg[0: self.width]
                                     .replace("\r", "").replace("\n", ""))
            self.cursesScreen.refresh()

    def readline(self):
        pass
