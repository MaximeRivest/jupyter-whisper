VERSION = (0, 1, 0, "beta", 1)
__version__ = ".".join(map(str, VERSION[:-2])) + "-" + VERSION[-2] + "." + str(VERSION[-1])
