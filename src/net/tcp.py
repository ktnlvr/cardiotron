"""
TCP stream read & write
"""

import gc
import io
import select
import socket
from collections import namedtuple

from net import defaulter_dict
from net.server import connection


class TCP:
    """TCP stream handler"""

    MSS = 536  # TCP/IP Maximum Segment Size

    class Writer(namedtuple("Writer", ["data", "buff", "buffmv", "range"])):
        pass

    def __init__(self, poller):
        self._poller = poller
        self._reads = {}  # Store read data by socket id
        self._writes = defaulter_dict()  # Store write data by socket id

    def read(self, sock):
        """Read data from socket"""
        sid = id(sock)
        try:
            request = self._reads.get(sid, b"") + sock.read()
        except:
            request = b""
            self.end(sock)
        self._reads[sid] = request
        return request

    def prepare(self, sock, data):
        """Prepare data for transmission"""
        buff = bytearray(b"00" * TCP.MSS)
        writers = self._writes.get(id(sock), [])
        writers.append(
            TCP.Writer(io.BytesIO(b"".join(data)), buff, memoryview(buff), [0, 0])
        )
        self._poller.modify(sock, select.POLLOUT)

    def write(self, sock):
        """Write next packet, return True if all packets written"""
        try:
            # Check if socket is still valid by trying to read from it
            sock.read()
            return True
        except:
            pass

        writers = self._writes.get(id(sock), [])
        if not writers:
            return True
        curr = writers[0]

        try:
            # Read from BytesIO into buffer
            data = curr.data.read(TCP.MSS)
            if not data:
                writers.remove(curr)
                return not writers

            # Copy data into buffer
            curr.buff[: len(data)] = data
            curr.range[1] = len(data)

            # Write from buffer
            bytes_written = sock.write(curr.buffmv[: curr.range[1]])
            if bytes_written == curr.range[1]:
                curr.range[0] = curr.range[1] = 0
            else:
                curr.range[0] += bytes_written
        except OSError:
            writers.remove(curr)
            return True
        return False

    def clear(self, sock):
        """Clear stored data for socket"""
        sid = id(sock)
        if sid in self._reads:
            del self._reads[sid]
        if sid in self._writes:
            del self._writes[sid]
        gc.collect()

    def end(self, sock):
        """Close socket and clean up"""
        try:
            while not self.write(sock):
                pass
        except:
            pass
        try:
            sock.close()
        except:
            pass
        try:
            self._poller.unregister(sock)
        except:
            pass
        self.clear(sock)
