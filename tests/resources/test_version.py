from twisted.internet.defer import inlineCallbacks

import hathor
from hathor.version_resource import VersionResource
from tests.resources.base_resource import StubSite, _BaseResourceTest


class BaseVersionTest(_BaseResourceTest._ResourceTest):
    __test__ = False

    def setUp(self):
        super().setUp()
        self.web = StubSite(VersionResource(self.manager))

    @inlineCallbacks
    def test_get(self):
        response = yield self.web.get("version")
        data = response.json_value()
        self.assertEqual(data['version'], hathor.__version__)


class SyncV1VersionTest(BaseVersionTest):
    __test__ = True

    _enable_sync_v1 = True
    _enable_sync_v2 = False


class SyncV2VersionTest(BaseVersionTest):
    __test__ = True

    _enable_sync_v1 = False
    _enable_sync_v2 = True


# sync-bridge should behave like sync-v2
class SyncBridgeVersionTest(SyncV2VersionTest):
    _enable_sync_v1 = True
