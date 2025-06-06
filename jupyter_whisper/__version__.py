VERSION = (0, 3, 0)
__version__ = ".".join(map(str, VERSION[:3]))
if len(VERSION) > 3:
    __version__ += "b" + str(VERSION[4])  # converts beta.2 to b2 format
