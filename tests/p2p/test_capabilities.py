from hathor.conf import HathorSettings
from hathor.simulator import FakeConnection
from tests import unittest

settings = HathorSettings()


class SyncV1HathorCapabilitiesTestCase(unittest.TestCase):
    _enable_sync_v1 = True
    _enable_sync_v2 = False

    def test_capabilities(self):
        network = 'testnet'
        manager1 = self.create_peer(network, capabilities=[settings.CAPABILITY_WHITELIST])
        manager2 = self.create_peer(network, capabilities=[])

        conn = FakeConnection(manager1, manager2)

        # Run the p2p protocol.
        for _ in range(100):
            conn.run_one_step(debug=True)
            self.clock.advance(0.1)

        # Even if we don't have the capability we must connect because the whitelist url conf is None
        self.assertEqual(conn._proto1.state.state_name, 'READY')
        self.assertEqual(conn._proto2.state.state_name, 'READY')

        manager3 = self.create_peer(network, capabilities=[settings.CAPABILITY_WHITELIST])
        manager4 = self.create_peer(network, capabilities=[settings.CAPABILITY_WHITELIST])

        conn2 = FakeConnection(manager3, manager4)

        # Run the p2p protocol.
        for _ in range(100):
            conn2.run_one_step(debug=True)
            self.clock.advance(0.1)

        self.assertEqual(conn2._proto1.state.state_name, 'READY')
        self.assertEqual(conn2._proto2.state.state_name, 'READY')


class SyncV2HathorCapabilitiesTestCase(unittest.TestCase):
    _enable_sync_v1 = False
    _enable_sync_v2 = True

    def test_capabilities(self):
        network = 'testnet'
        manager1 = self.create_peer(network, capabilities=[settings.CAPABILITY_WHITELIST, settings.CAPABILITY_SYNC_V2])
        manager2 = self.create_peer(network, capabilities=[settings.CAPABILITY_SYNC_V2])

        conn = FakeConnection(manager1, manager2)

        # Run the p2p protocol.
        for _ in range(100):
            conn.run_one_step(debug=True)
            self.clock.advance(0.1)

        # Even if we don't have the capability we must connect because the whitelist url conf is None
        self.assertEqual(conn._proto1.state.state_name, 'READY')
        self.assertEqual(conn._proto2.state.state_name, 'READY')

        manager3 = self.create_peer(network, capabilities=[settings.CAPABILITY_WHITELIST, settings.CAPABILITY_SYNC_V2])
        manager4 = self.create_peer(network, capabilities=[settings.CAPABILITY_WHITELIST, settings.CAPABILITY_SYNC_V2])

        conn2 = FakeConnection(manager3, manager4)

        # Run the p2p protocol.
        for _ in range(100):
            conn2.run_one_step(debug=True)
            self.clock.advance(0.1)

        self.assertEqual(conn2._proto1.state.state_name, 'READY')
        self.assertEqual(conn2._proto2.state.state_name, 'READY')


# sync-bridge should behave like sync-v2
class SyncBridgeHathorCapabilitiesTestCase(SyncV2HathorCapabilitiesTestCase):
    _enable_sync_v1 = True
