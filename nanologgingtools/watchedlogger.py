"""logger.py: WatchedTimedRotatingFileHandler"""

import os
import errno
from stat import ST_DEV, ST_INO
import logging.handlers

__author__ = "Raido Pahtma"
__license__ = "MIT"


class WatchedTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """*** Watching functionality copied from python 2.7 WatchedFileHandler ***"""

    def __init__(self, *args, **kwargs):
        super(WatchedTimedRotatingFileHandler, self).__init__(*args, **kwargs)
        self.dev, self.ino = -1, -1
        self._statstream()

    def _statstream(self):
        if self.stream:
            sres = os.fstat(self.stream.fileno())
            self.dev, self.ino = sres[ST_DEV], sres[ST_INO]

    def emit(self, record):
        try:
            sres = os.stat(self.baseFilename)
        except OSError as err:
            if err.errno == errno.ENOENT:
                sres = None
            else:
                raise
        # compare file system stat with that of our stream file handle
        if not sres or sres[ST_DEV] != self.dev or sres[ST_INO] != self.ino:
            if self.stream is not None:
                # we have an open file handle, clean it up
                self.stream.flush()
                self.stream.close()
                self.stream = None  # See Issue #21742: _open () might fail.
                # open a new file handle and get new stat info from that fd
                self.stream = self._open()
                self._statstream()

        super(WatchedTimedRotatingFileHandler, self).emit(record)
