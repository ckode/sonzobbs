from sqlalchemy import Column, Integer, String, func
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper, sessionmaker

#from bbs.accounts import ACCT
LOGOFF = 0
MENU = 1
DOOR = 2


engine = create_engine('sqlite:///data/menus.db', echo=False)

Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class MenuOptionException(Exception):
    """
    Menu Option Exception raise for invalid menu
    options and when BBS door selected.
    """
    def __init__(self, msg):
        """
        Initialize the exception and message.
        """
        self.message = msg

    def __repr__(self):
        return self.message


class Menu(Base):
    """
    Sonzo BBS Menu System Class
    """

    __tablename__ = 'menus'

    id = Column(Integer, primary_key=True)
    menudepth = Column(Integer, unique=True, nullable=False)
    menutitle = Column(String, nullable=False)
    menutext = Column(String, nullable=False)
    menucolor = Column(String)
    menuname = Column(String, nullable=False, unique=True)
    backmenu = Column(String, nullable=False)


    def __repr__(self):
        return "Menu Class Object"


class MenuOption(Base):
    """
    Sonzo BBS Menu Option Class
    """

    __tablename__ = 'menuoptions'

    id = Column(Integer, primary_key=True)
    menuname = Column(String, nullable=False)
    optiontext = Column(String, nullable=False)
    menuoption = Column(String, nullable=False)
    optiontype = Column(Integer, nullable=False)
    destination = Column(String, nullable=False)
    menuorder = Column(Integer, nullable=False)


    def __repr__(self):
        return "MenuOption Class Object"


def menuOptionSelected(client, option):
    """
    Process menu option selected.
    """
    q = session.query(Menu).filter_by(menuname = client.getMenu()).first()


    if q.menuname == 'LOGOFF':
        if option.lower() == 'y':
            raise MenuOptionException('LOGOFF')
        elif option == '?':
            client.setMenu('LOGOFF')
        else:
            client.setMenu('MAINMENU')
            return True

    if option.lower() == "x":
        client.setMenu(q.backmenu)
        return True
    elif option == '?':
        return True

    if option.lower() in { e.lower() for e in getMenuOptions(client.getMenu()) }:
        menuopt = session.query(MenuOption).filter(MenuOption.menuname == client.getMenu()).\
                                            filter(func.lower(MenuOption.menuoption) == func.lower(option)).\
                                            first()

    else:
        raise MenuOptionException('INVALID')

    if menuopt.optiontype is DOOR:
        raise MenuOptionException(menuopt.destination)
    else:
       client.setMenu(menuopt.destination)
       return True


def getMenuOptions(menu):
    """
    Return current menu options.
    """

    q = session.query(MenuOption).filter_by(menuname = menu).order_by(MenuOption.menuorder)
    opts = []
    for o in q:
        opts.append(o.menuoption)

    if menu == 'LOGOFF':
        opts.extend(['X', 'Y', 'N', '?'])
    else:
        opts.extend(['X', '?'])
    return opts


def getDestinationCode(menu, selectedoption):
    """
    Get destination code from selected menu option.
    """

    q = session.query(MenuOption).filter_by(menuname = menu, menuoption = selectedoption).first()

    if not q:
        return False
    else:
        return q.destination


def getMiniMenu(client):
    """
    Return mini menu options text.
    """
    menuname = client.getMenu()
    optionstxt = "\n^G(^M{}^G)\nMake your selection ({} ? for ^Mhelp^G or X for ^Mexit^g): "
    opts = getMenuOptions(menuname)
    mname = getMenuTitle(menuname)
    ostr = ""

    if opts:
        for o in opts:
            # Don't display empty options (y/n for logoff is one)
            if o == "":
                continue
            ostr = ostr + "{},".format(o)

        if mname:
            return optionstxt.format(mname, ostr)

    return False


def getFullMenu(client):
    """
    Get full menu screen.
    """
    menu = client.getMenu()
    q = session.query(MenuOption).filter_by(menuname = menu).order_by(MenuOption.menuorder)
    title = getMenuTitle(client.getMenu())

    mstr = title.rjust(40, ' ')
    mstr = "^s\n\n\n\n\n\n\n\n\n\n\n\n^M{}\n\n".format(mstr)
    spaces = "                             "
    arry = []
    if menu == 'LOGOFF':
        mstr = "{}^MLog off? (^GY^M / ^GN^M)".format(spaces)
    else:
        for o in q:
            spaced = "{}[^M{}^G] {}\n".format(spaces, o.menuoption, o.optiontext)
            arry.append("^G{}".format(spaced))

        for line in arry:
            mstr = "{}{}".format(mstr, line)

    return "\n{}{}".format(mstr, getMiniMenu(client))


def getMenuTitle(menu):
    """
    Get Menu's Name
    """
    q = session.query(Menu).filter(Menu.menuname == menu).first()
    if not q:
        return False
    else:
        return q.menutitle


def isValidMenuSelection(client, selection):
    """
    Check if the client's menu selection valid.
    """

    if selection in getMenuOptions(client.getValue(3)):
        return True

    return False

def getLoginScreen():
    screen = """\n\n       ^MWELCOME to SonzoBBS!

^GIf you already have a User-ID on this
system, type it in and press ENTER.
Otherwise type "^Cnew^G": ^w"""

    return screen
    
 
def getPasswordScreen():
    """
    Return text screen for getting password,
    """
    return "^GEnter your password: ^w"

    
def verifyMenuDatabase():
    """
    Verify that a menu database exists, if not
    create one.
    """

    q = session.query(Menu)
    if q.count() < 2:
        logoffmenu = Menu(menudepth=0, menutitle='Log Off', menutext='Do you wish to log off?', menucolor='^M', menuname='LOGOFF', backmenu='LOGOFF')
        mainmenu = Menu(menudepth=1, menutitle='Main Menu', menutext='Welcome to Sonzo BBS!', menucolor='^M', menuname='MAINMENU', backmenu='LOGOFF')
        gamesmenu = Menu(menudepth=2, menutitle='Games', menutext='Sonzo BBS Games', menucolor='^M', menuname='GAMES', backmenu='MAINMENU')
        session.add(logoffmenu)
        session.add(mainmenu)
        session.commit()

    q = session.query(MenuOption)
    if q.count() < 2:
        logoffback = MenuOption(menuname='LOGOFF', optiontext="Log off?", menuoption="", optiontype=LOGOFF, destination='DISCONNECT', menuorder=1)
        messages = MenuOption(menuname='MAINMENU', optiontext="Messages", menuoption="M", optiontype=DOOR, destination='MESSAGES', menuorder=1)
        games = MenuOption(menuname='MAINMENU', optiontext="Games", menuoption="G", optiontype=MENU, destination='GAMES', menuorder=3)
        teleconference = MenuOption(menuname='MAINMENU', optiontext="Teleconference", menuoption="T", optiontype=DOOR, destination='TELECONFERENCE', menuorder=2)
        majormud = MenuOption(menuname='GAMES', optiontext="MajorMUD", menuoption="M", optiontype=DOOR, destination='MAJORMUD1', menuorder=1)
        minions = MenuOption(menuname='GAMES', optiontext="Minions", menuoption="N", optiontype=DOOR, destination='MINIONS', menuorder=2)
        arena = MenuOption(menuname='GAMES', optiontext="ArenaMUD", menuoption="A", optiontype=DOOR, destination='ARENAMUD', menuorder=3)
        lord = MenuOption(menuname='GAMES', optiontext="Legend of the Red Dragon", menuoption="R", optiontype=DOOR, destination='LORD', menuorder=4)

        session.add(logoffback)
        session.add(messages)
        session.add(gamesmenu)
        session.add(games)
        session.add(teleconference)
        session.add(majormud)
        session.add(minions)
        session.add(arena)
        session.add(lord)
        session.commit()


Base.metadata.create_all(engine, checkfirst=True)
