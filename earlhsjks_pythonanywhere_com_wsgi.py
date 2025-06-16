import sys
path = '/home/earlhsjks/gia_attendance'  # or your actual project folder
if path not in sys.path:
    sys.path.insert(0, path)

from gia_attendance import app as application  # noqa
