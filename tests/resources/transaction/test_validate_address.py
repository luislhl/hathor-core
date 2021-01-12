from twisted.internet.defer import inlineCallbacks

from hathor.transaction.resources import ValidateAddressResource
from tests.resources.base_resource import StubSite, _BaseResourceTest


class BaseTransactionTest(_BaseResourceTest._ResourceTest):
    __test__ = False

    def setUp(self):
        super().setUp()
        self.web = StubSite(ValidateAddressResource(self.manager))

    # Example from the design:
    #
    # ❯ curl localhost:9080/v1a/validate_address/HNXsVtRUmwDCtpcCJUrH4QiHo9kUKx199A -s | jq
    # {
    #   "valid": true,
    #   "script": "dqkUr6YAVWv0Ps6bjgSGuqMb1GqCw6+IrA==",
    #   "address": "HNXsVtRUmwDCtpcCJUrH4QiHo9kUKx199A",
    #   "type": "p2pkh"
    # }

    @inlineCallbacks
    def test_simple(self):
        address = b'HNXsVtRUmwDCtpcCJUrH4QiHo9kUKx199A'
        response_success = yield self.web.get(address)
        data_success = response_success.json_value()
        self.assertEqual(data_success, {
           'valid': True,
           'script': 'dqkUr6YAVWv0Ps6bjgSGuqMb1GqCw6+IrA==',
           'address': address.decode('ascii'),
           'type': 'p2pkh',
        })

    @inlineCallbacks
    def test_invalid_network(self):
        # this address is valid on the testnet
        response_success = yield self.web.get(b'WTPcVyGjo9tSet8QAH7qudW2LwtkgubZGU')
        data_success = response_success.json_value()
        self.assertEqual(data_success, {
           'valid': False,
           'error': 'ScriptError',
           'msg': 'The address is not valid',
        })

    @inlineCallbacks
    def test_wrong_size(self):
        address = b'HNXsVtRUmwDCtpcCJUrH4QiHo9kUKx199Aa'
        response_success = yield self.web.get(address)
        data_success = response_success.json_value()
        self.assertEqual(data_success, {
           'valid': False,
           'error': 'InvalidAddress',
           'msg': 'Address size must have 25 bytes',
        })

    @inlineCallbacks
    def test_gibberish(self):
        # this isn't remotely what an address looks like
        response_success = yield self.web.get(b'ahl8sfyoiuh23$%!!dfads')
        data_success = response_success.json_value()
        self.assertEqual(data_success, {
           'valid': False,
           'error': 'InvalidAddress',
           'msg': 'Invalid base58 address',
        })


class SyncV1TransactionTest(BaseTransactionTest):
    __test__ = True

    _enable_sync_v1 = True
    _enable_sync_v2 = False


class SyncV2TransactionTest(BaseTransactionTest):
    __test__ = True

    _enable_sync_v1 = False
    _enable_sync_v2 = True


# sync-bridge should behave like sync-v2
class SyncBridgeTransactionTest(SyncV2TransactionTest):
    _enable_sync_v1 = True
