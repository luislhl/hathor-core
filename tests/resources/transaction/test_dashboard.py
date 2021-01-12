from twisted.internet.defer import inlineCallbacks

from hathor.transaction.resources import DashboardTransactionResource
from tests.resources.base_resource import StubSite, _BaseResourceTest


class BaseDashboardTest(_BaseResourceTest._ResourceTest):
    __test__ = False

    def setUp(self):
        super().setUp()
        self.web = StubSite(DashboardTransactionResource(self.manager))

    @inlineCallbacks
    def test_get(self):
        tx_count = block_count = 6
        response = yield self.web.get("dashboard_tx", {
            b'block': str(block_count).encode(),
            b'tx': str(tx_count).encode()
        })
        data = response.json_value()

        self.assertLessEqual(len(data['transactions']), tx_count)
        self.assertLessEqual(len(data['blocks']), block_count)

    @inlineCallbacks
    def test_invalid_parameters(self):
        # wrong type block
        response = yield self.web.get("dashboard_tx", {b'block': b'a', b'tx': b'6'})
        data = response.json_value()
        self.assertFalse(data['success'])
        # missing block param
        response = yield self.web.get("dashboard_tx", {b'tx': b'6'})
        data = response.json_value()
        self.assertFalse(data['success'])

        # wrong type tx
        response = yield self.web.get("dashboard_tx", {b'block': b'6', b'tx': b'a'})
        data = response.json_value()
        self.assertFalse(data['success'])
        # missing tx param
        response = yield self.web.get("dashboard_tx", {b'block': b'6'})
        data = response.json_value()
        self.assertFalse(data['success'])


class SyncV1DashboardTest(BaseDashboardTest):
    __test__ = True

    _enable_sync_v1 = True
    _enable_sync_v2 = False


class SyncV2DashboardTest(BaseDashboardTest):
    __test__ = True

    _enable_sync_v1 = False
    _enable_sync_v2 = True


# sync-bridge should behave like sync-v2
class SyncBridgeDashboardTest(SyncV2DashboardTest):
    _enable_sync_v1 = True
