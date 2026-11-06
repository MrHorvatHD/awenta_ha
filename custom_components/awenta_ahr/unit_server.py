"""Local server the Awenta units connect to instead of wss://ahr.awenta.pl:31990/ (pure asyncio, no Home Assistant imports).

The units are websocket *clients*: they open a TLS connection to the cloud's address, upgrade to a websocket and then send
binary frames (state reports every ~5 s) while the server pings them. They do not check the server's certificate, so a
self-signed certificate is enough once the name `ahr.awenta.pl` resolves to the machine running this server.
"""
import asyncio
import base64
import hashlib
import logging
import ssl
import struct

try:
    from . import frames
except ImportError:  # imported as a top-level module (tests)
    import frames

_LOGGER = logging.getLogger(__name__)

WS_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_FRAME = 65536


class _Connection:
    """One connected unit (its MAC is learned from the first report)."""

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.mac = None
        self.timezone = None
        self._lock = asyncio.Lock()

    async def send(self, opcode, payload=b""):
        async with self._lock:
            self.writer.write(frames.ws_frame(opcode, payload))
            await self.writer.drain()

    def close(self):
        try:
            self.writer.close()
        except Exception:  # noqa: BLE001 - already closing
            pass


class UnitServer:
    def __init__(self, port, ssl_context, on_report, on_connected=None, on_disconnected=None,
                 host="0.0.0.0", ping_interval=10, idle_timeout=60):
        self.port = port
        self.host = host
        self._ssl = ssl_context
        self._on_report = on_report
        self._on_connected = on_connected or (lambda mac: None)
        self._on_disconnected = on_disconnected or (lambda mac: None)
        self._ping_interval = ping_interval
        self._idle_timeout = idle_timeout
        self._server = None
        self._conns = {}
        self._tasks = set()

    async def start(self):
        self._server = await asyncio.start_server(self._handle, self.host, self.port, ssl=self._ssl)
        if self.port == 0:  # tests: let the OS choose
            self.port = self._server.sockets[0].getsockname()[1]
        _LOGGER.info("Awenta unit server listening on %s:%s", self.host, self.port)

    async def stop(self):
        if self._server is not None:
            self._server.close()
        for conn in list(self._conns.values()):
            conn.close()
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._server is not None:
            try:
                await asyncio.wait_for(self._server.wait_closed(), 5)
            except asyncio.TimeoutError:
                pass
            self._server = None
        self._conns.clear()

    def online(self, mac):
        return mac in self._conns

    def online_macs(self):
        return list(self._conns)

    def timezone(self, mac):
        conn = self._conns.get(mac)
        return conn.timezone if conn else None

    async def send(self, mac, payloads):
        """Scramble and send unit payloads (command bytes) to a connected unit."""
        conn = self._conns.get(mac)
        if conn is None:
            raise ConnectionError(f"unit {mac} is not connected")
        for payload in payloads:
            await conn.send(2, frames.encode_command(payload))

    # -- connection handling ------------------------------------------------------------------------------------

    async def _handle(self, reader, writer):
        task = asyncio.current_task()
        self._tasks.add(task)
        conn = _Connection(reader, writer)
        pinger = None
        try:
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
            key = None
            for line in head.split(b"\r\n")[1:]:
                if line.lower().startswith(b"sec-websocket-key:"):
                    key = line.split(b":", 1)[1].strip()
            if key is None:
                writer.write(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
                await writer.drain()
                return
            accept = base64.b64encode(hashlib.sha1(key + WS_GUID).digest())
            writer.write(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                         b"Sec-WebSocket-Accept: " + accept + b"\r\n\r\n")
            await writer.drain()
            pinger = asyncio.create_task(self._pinger(conn))
            await self._read_loop(conn)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError,
                ssl.SSLError, OSError):
            pass
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - never let one unit take the server down
            _LOGGER.exception("Awenta unit connection failed")
        finally:
            if pinger is not None:
                pinger.cancel()
            was_current = conn.mac is not None and self._conns.get(conn.mac) is conn
            if was_current:
                del self._conns[conn.mac]
            conn.close()
            self._tasks.discard(task)
            if was_current:
                try:
                    self._on_disconnected(conn.mac)
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Awenta disconnect callback failed")

    async def _pinger(self, conn):
        try:
            while True:
                await asyncio.sleep(self._ping_interval)
                await conn.send(9)
        except (asyncio.CancelledError, ConnectionError, OSError, ssl.SSLError):
            return

    async def _read_loop(self, conn):
        reader = conn.reader
        while True:
            b0, b1 = await asyncio.wait_for(reader.readexactly(2), self._idle_timeout)
            opcode, length, masked = b0 & 0x0F, b1 & 0x7F, bool(b1 & 0x80)
            if length == 126:
                length = struct.unpack(">H", await reader.readexactly(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", await reader.readexactly(8))[0]
            if length > MAX_FRAME:
                raise ConnectionError("frame too large")
            mask = await reader.readexactly(4) if masked else b""
            payload = await reader.readexactly(length)
            if masked:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 8:
                return
            if opcode == 9:
                await conn.send(10, payload)
            elif opcode == 2 and b0 & 0x80:
                self._handle_report(conn, payload)
            # pongs, text and fragmented frames are not used by the units

    def _handle_report(self, conn, frame):
        try:
            payload = frames.decode_report(frame)
        except ValueError:
            _LOGGER.debug("Awenta: dropping a frame with a bad checksum")
            return
        if len(payload) < 7:
            return
        mac = frames.mac_of(payload)
        if conn.mac != mac:
            old = self._conns.get(mac)
            if old is not None and old is not conn:
                old.close()
            conn.mac = mac
            self._conns[mac] = conn
            self._on_connected(mac)
        kind = payload[6]
        if kind == 1:
            state = frames.parse_state(payload)
            if state is not None:
                self._on_report(mac, state)
        elif kind == 3:
            conn.timezone = frames.parse_timezone(payload)
