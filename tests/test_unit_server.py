"""Unit server tests with a fake unit (stdlib only): python3 -m unittest discover -s tests"""
import asyncio
import base64
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from _load import load  # noqa: E402

frames = load("frames")
unit_server = load("unit_server")
from test_protocol import REPORT, TZ_REPORT  # noqa: E402

MAC = "8C:4B:14:CA:2A:B4"


_CTX = None


def make_cert(directory):
    """One throwaway certificate for the whole test run (openssl keygen is slow)."""
    global _CTX
    if _CTX is not None:
        return _CTX
    cert, key = os.path.join(directory, "c.pem"), os.path.join(directory, "k.pem")
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2", "-subj", "/CN=ahr.awenta.pl",
         "-keyout", key, "-out", cert],
        check=True, capture_output=True)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(cert, key)
    _CTX = ctx
    return ctx


class FakeUnit:
    """Behaves like the ESP32 websocket client: TLS without certificate checks, masked frames."""

    def __init__(self, port):
        self.port = port

    async def connect(self, handshake=True):
        ctx = ssl.create_default_context()
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        self.reader, self.writer = await asyncio.open_connection("127.0.0.1", self.port, ssl=ctx,
                                                                 server_hostname="ahr.awenta.pl")
        key = base64.b64encode(os.urandom(16))
        request = (b"GET / HTTP/1.1\r\nConnection: Upgrade\r\nHost: ahr.awenta.pl:31990\r\n"
                   b"User-Agent: ESP32 Websocket Client\r\nUpgrade: websocket\r\nSec-WebSocket-Version: 13\r\n")
        if handshake:
            request += b"Sec-WebSocket-Key: " + key + b"\r\n"
        self.writer.write(request + b"\r\n")
        await self.writer.drain()
        self.response = await self.reader.readuntil(b"\r\n\r\n")

    async def send(self, opcode, payload=b""):
        mask = os.urandom(4)
        n = len(payload)
        if n < 126:
            head = bytes([0x80 | opcode, 0x80 | n])
        else:
            head = bytes([0x80 | opcode, 0x80 | 126]) + n.to_bytes(2, "big")
        self.writer.write(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
        await self.writer.drain()

    async def recv(self, timeout=3):
        b0, b1 = await asyncio.wait_for(self.reader.readexactly(2), timeout)
        n = b1 & 0x7F
        if n == 126:
            n = int.from_bytes(await self.reader.readexactly(2), "big")
        return b0 & 0x0F, await self.reader.readexactly(n)

    async def close(self):
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except (OSError, ssl.SSLError):
            pass


class ServerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.dir = tempfile.mkdtemp()
        self.ctx = make_cert(self.dir)
        self.reports, self.connected, self.disconnected = [], [], []
        self.server = None

    async def asyncTearDown(self):
        if self.server:
            await self.server.stop()
        shutil.rmtree(self.dir, ignore_errors=True)

    async def start(self, **kwargs):
        self.server = unit_server.UnitServer(
            0, self.ctx, lambda mac, state: self.reports.append((mac, state)), self.connected.append,
            self.disconnected.append, host="127.0.0.1", **kwargs)
        await self.server.start()
        return FakeUnit(self.server.port)

    async def wait_for(self, predicate, timeout=3):
        end = asyncio.get_event_loop().time() + timeout
        while not predicate():
            if asyncio.get_event_loop().time() > end:
                self.fail("condition not reached")
            await asyncio.sleep(0.02)

    async def test_report_is_parsed_and_unit_marked_online(self):
        unit = await self.start()
        await unit.connect()
        self.assertIn(b"101 Switching Protocols", unit.response)
        await unit.send(2, frames.encode_report(TZ_REPORT))
        await unit.send(2, frames.encode_report(REPORT))
        await self.wait_for(lambda: self.reports)
        mac, state = self.reports[0]
        self.assertEqual(mac, MAC)
        self.assertEqual((state["power"], state["recuperation_gear_adv"], state["humidity_sensor"]), (True, 3, 639))
        self.assertEqual(self.connected, [MAC])
        self.assertTrue(self.server.online(MAC))
        self.assertEqual(self.server.timezone(MAC), "CET-1CEST,M3.5.0,M10.5.0/3")
        await unit.close()

    async def test_commands_reach_the_unit_scrambled(self):
        unit = await self.start()
        await unit.connect()
        await unit.send(2, frames.encode_report(REPORT))
        await self.wait_for(lambda: self.server.online(MAC))
        await self.server.send(MAC, frames.command_payloads({"act": "set_time_manual", "h": 13, "m": 10}))
        got = []
        for _ in range(2):
            opcode, data = await unit.recv()
            self.assertEqual(opcode, 2)
            got.append(frames.decode_command(data))
        self.assertEqual(got[1], b"\x0e\x03\x16")
        self.assertTrue(got[0].startswith(b"\x04\x00\x00CET"))
        await unit.close()

    async def test_server_pings_and_answers_pings(self):
        unit = await self.start(ping_interval=0.2)
        await unit.connect()
        await unit.send(2, frames.encode_report(REPORT))
        opcode, _ = await unit.recv()
        self.assertEqual(opcode, 9)
        await unit.send(9, b"hi")
        while True:
            opcode, data = await unit.recv()
            if opcode == 10:
                self.assertEqual(data, b"hi")
                break
        await unit.close()

    async def test_disconnect_is_reported(self):
        unit = await self.start()
        await unit.connect()
        await unit.send(2, frames.encode_report(REPORT))
        await self.wait_for(lambda: self.server.online(MAC))
        await unit.close()
        await self.wait_for(lambda: self.disconnected)
        self.assertEqual(self.disconnected, [MAC])
        self.assertFalse(self.server.online(MAC))
        with self.assertRaises(ConnectionError):
            await self.server.send(MAC, [b"\x05\x01"])

    async def test_reconnect_replaces_the_old_connection_quietly(self):
        first = await self.start()
        await first.connect()
        await first.send(2, frames.encode_report(REPORT))
        await self.wait_for(lambda: self.server.online(MAC))
        second = FakeUnit(first.port)
        await second.connect()
        await second.send(2, frames.encode_report(REPORT))
        await self.wait_for(lambda: len(self.connected) == 2)
        await asyncio.sleep(0.2)
        self.assertTrue(self.server.online(MAC))
        self.assertEqual(self.disconnected, [])  # the old socket closing must not mark the unit offline
        await second.close()
        await first.close()

    async def test_bad_checksum_is_ignored(self):
        unit = await self.start()
        await unit.connect()
        bad = bytearray(frames.encode_report(REPORT))
        bad[5] ^= 0x55
        await unit.send(2, bytes(bad))
        await unit.send(2, frames.encode_report(REPORT))
        await self.wait_for(lambda: self.reports)
        self.assertEqual(len(self.reports), 1)
        await unit.close()

    async def test_plain_http_is_rejected(self):
        unit = await self.start()
        await unit.connect(handshake=False)
        self.assertIn(b"400", unit.response)
        await unit.close()

    async def test_idle_connection_is_dropped(self):
        unit = await self.start(idle_timeout=0.4)
        await unit.connect()
        await unit.send(2, frames.encode_report(REPORT))
        await self.wait_for(lambda: self.server.online(MAC))
        await self.wait_for(lambda: self.disconnected, timeout=3)
        await unit.close()


if __name__ == "__main__":
    unittest.main()
