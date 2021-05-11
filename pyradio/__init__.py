" pyradio -- Console radio player. "

version_info = (0, 8, 9, 2)

# Application state:
# New stable version:  ''
# Beta version:        'betax', x=1,2,3...
# RC version:          'RCx', x=1,23...
app_state = ''

# Set it to True if new stations have been
# added to the package's stations.csv
stations_updated = False


__version__ = version = '.'.join(map(str, version_info))
__project__ = __name__
__author__ = "Ben Dowling"
__license__ = "MIT"
