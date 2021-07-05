import random
import sys
from typing import Optional

import pytest

from hathor.simulator import FakeConnection, MinerSimulator, RandomTransactionGenerator, Simulator
from tests import unittest


@pytest.mark.skipif(sys.platform == 'win32', reason='set_seed fails on Windows')
class BaseHathorSimulatorTestCase(unittest.TestCase):
    __test__ = False

    seed_config: Optional[int] = None

    def setUp(self):
        super().setUp()

        self.clock = None

        if self.seed_config is None:
            self.seed_config = random.randint(0, 2**32 - 1)

        self.simulator = Simulator()
        self.simulator.set_seed(self.seed_config)
        self.simulator.start()

        print('-'*30)
        print('Simulation seed config:', self.simulator.seed)
        print('-'*30)

    def tearDown(self):
        self.simulator.stop()
        super().tearDown()

    def create_peer(self, enable_sync_v1=None, enable_sync_v2=None):
        if enable_sync_v1 is None:
            assert hasattr(self, '_enable_sync_v1'), ('`_enable_sync_v1` has no default by design, either set one on '
                                                      'the test class or pass `enable_sync_v1` by argument')
            enable_sync_v1 = self._enable_sync_v1
        if enable_sync_v2 is None:
            assert hasattr(self, '_enable_sync_v2'), ('`_enable_sync_v2` has no default by design, either set one on '
                                                      'the test class or pass `enable_sync_v2` by argument')
            enable_sync_v2 = self._enable_sync_v2
        assert enable_sync_v1 or enable_sync_v2, 'enable at least one sync version'
        return self.simulator.create_peer(enable_sync_v1=enable_sync_v1, enable_sync_v2=enable_sync_v2)

    def test_one_node(self):
        manager1 = self.create_peer()

        miner1 = MinerSimulator(manager1, hashpower=100e6)
        miner1.start()
        self.simulator.run(10)

        gen_tx1 = RandomTransactionGenerator(manager1, rate=2 / 60., hashpower=1e6, ignore_no_funds=True)
        gen_tx1.start()
        self.simulator.run(60 * 60)

    def test_two_nodes(self):
        manager1 = self.create_peer()
        manager2 = self.create_peer()

        miner1 = MinerSimulator(manager1, hashpower=10e6)
        miner1.start()
        self.simulator.run(10)

        gen_tx1 = RandomTransactionGenerator(manager1, rate=3 / 60., hashpower=1e6, ignore_no_funds=True)
        gen_tx1.start()
        self.simulator.run(60)

        conn12 = FakeConnection(manager1, manager2, latency=0.150)
        self.simulator.add_connection(conn12)
        self.simulator.run(60)

        miner2 = MinerSimulator(manager2, hashpower=100e6)
        miner2.start()
        self.simulator.run(120)

        gen_tx2 = RandomTransactionGenerator(manager2, rate=10 / 60., hashpower=1e6, ignore_no_funds=True)
        gen_tx2.start()
        self.simulator.run(10 * 60)

        miner1.stop()
        miner2.stop()
        gen_tx1.stop()
        gen_tx2.stop()

        self.simulator.run(5 * 60)

        self.assertTrue(conn12.is_connected)
        self.assertTipsEqual(manager1, manager2)

    def test_many_miners_since_beginning(self):
        nodes = []
        miners = []

        for hashpower in [10e6, 5e6, 1e6, 1e6, 1e6]:
            manager = self.create_peer()
            for node in nodes:
                conn = FakeConnection(manager, node, latency=0.085)
                self.simulator.add_connection(conn)

            nodes.append(manager)

            miner = MinerSimulator(manager, hashpower=hashpower)
            miner.start()
            miners.append(miner)

        self.simulator.run(600)

        for miner in miners:
            miner.stop()

        self.simulator.run(15)

        for node in nodes[1:]:
            self.assertTipsEqual(nodes[0], node)

    def test_new_syncing_peer(self):
        nodes = []
        miners = []
        tx_generators = []

        manager = self.create_peer()
        nodes.append(manager)
        miner = MinerSimulator(manager, hashpower=10e6)
        miner.start()
        miners.append(miner)
        self.simulator.run(600)

        for hashpower in [10e6, 8e6, 5e6]:
            manager = self.create_peer()
            for node in nodes:
                conn = FakeConnection(manager, node, latency=0.085)
                self.simulator.add_connection(conn)
            nodes.append(manager)

            miner = MinerSimulator(manager, hashpower=hashpower)
            miner.start()
            miners.append(miner)

        for i, rate in enumerate([5, 4, 3]):
            tx_gen = RandomTransactionGenerator(nodes[i], rate=rate * 1 / 60., hashpower=1e6, ignore_no_funds=True)
            tx_gen.start()
            tx_generators.append(tx_gen)

        self.simulator.run(600)

        self.log.debug('adding late node')
        late_manager = self.create_peer()
        for node in nodes:
            conn = FakeConnection(late_manager, node, latency=0.300)
            self.simulator.add_connection(conn)

        self.simulator.run(600)

        for tx_gen in tx_generators:
            tx_gen.stop()
        for miner in miners:
            miner.stop()

        # XXX: maybe there should be a simulator.run_until_synced(max_steps), instead of blindly stepping >600 times
        self.simulator.run(2000)

        for idx, node in enumerate(nodes):
            self.log.debug(f'checking node {idx}')
            self.assertConsensusValid(node)
            self.assertConsensusEqual(node, late_manager)


class SyncV1HathorSimulatorTestCase(BaseHathorSimulatorTestCase):
    __test__ = True

    _enable_sync_v1 = True
    _enable_sync_v2 = False


class SyncV2HathorSimulatorTestCase(BaseHathorSimulatorTestCase):
    __test__ = True

    _enable_sync_v1 = False
    _enable_sync_v2 = True

    # XXX: override methods to mark as flaky only on sync-v2
    # XXX: these may or may not be related to https://github.com/HathorNetwork/sec-hathor-core/issues/70

    # XXX: retry the test once if it fails, see: https://github.com/box/flaky
    @pytest.mark.flaky
    def test_new_syncing_peer(self):
        super().test_new_syncing_peer()

    @pytest.mark.flaky
    def test_two_nodes(self):
        super().test_two_nodes()


# sync-bridge should behave like sync-v2
class SyncBridgeHathorSimulatorTestCase(SyncV2HathorSimulatorTestCase):
    _enable_sync_v1 = True
