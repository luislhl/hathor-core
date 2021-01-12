from twisted.internet.defer import inlineCallbacks

from hathor.p2p.peer_id import PeerId
from hathor.p2p.resources import AddPeersResource
from tests.resources.base_resource import StubSite, _BaseResourceTest


class BaseAddPeerTest(_BaseResourceTest._ResourceTest):
    __test__ = False

    def setUp(self):
        super().setUp()
        self.web = StubSite(AddPeersResource(self.manager))

    @inlineCallbacks
    def test_connecting_peers(self):
        response = yield self.web.post('p2p/peers', ['tcp://localhost:8006'])
        data = response.json_value()
        self.assertTrue(data['success'])

        # test when we send a peer we're already connected to
        peer = PeerId()
        peer.entrypoints = ['tcp://localhost:8006']
        self.manager.connections.peer_storage.add(peer)
        response = yield self.web.post('p2p/peers', ['tcp://localhost:8006', 'tcp://localhost:8007'])
        data = response.json_value()
        self.assertTrue(data['success'])
        self.assertEqual(data['peers'], ['tcp://localhost:8007'])

    @inlineCallbacks
    def test_invalid_data(self):
        # no data
        response = yield self.web.post('p2p/peers')
        data = response.json_value()
        self.assertFalse(data['success'])

        # invalid type
        response = yield self.web.post('p2p/peers', {'a': 'tcp://localhost:8006'})
        data = response.json_value()
        self.assertFalse(data['success'])


class SyncV1AddPeerTest(BaseAddPeerTest):
    __test__ = True

    _enable_sync_v1 = True
    _enable_sync_v2 = False


class SyncV2AddPeerTest(BaseAddPeerTest):
    __test__ = True

    _enable_sync_v1 = False
    _enable_sync_v2 = True


# sync-bridge should behave like sync-v2
class SyncBridgeAddPeerTest(SyncV2AddPeerTest):
    _enable_sync_v1 = True
