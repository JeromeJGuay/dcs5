import curses

def main(stdscr: curses.window):
    stdscr.clear()
    stdscr.addstr('test')
    stdscr.refresh()
    stdscr.getch()

curses.wrapper(main)