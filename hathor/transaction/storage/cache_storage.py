# Copyright 2021 Hathor Labs
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Optional, Set

from twisted.internet import threads

from hathor.transaction import BaseTransaction
from hathor.transaction.storage.transaction_storage import BaseTransactionStorage

if TYPE_CHECKING:
    from twisted.internet import Reactor


class TransactionCacheStorage(BaseTransactionStorage):
    """Caching storage to be used 'on top' of other storages.
    """

    cache: 'OrderedDict[bytes, BaseTransaction]'
    dirty_txs: Set[bytes]

    def __init__(self, store: 'BaseTransactionStorage', reactor: 'Reactor', interval: int = 5,
                 capacity: int = 10000, *, _clone_if_needed: bool = False, with_all_index: bool = False):
        """
        :param store: a subclass of BaseTransactionStorage
        :type store: :py:class:`hathor.transaction.storage.BaseTransactionStorage`

        :param reactor: Twisted reactor which handles the mainloop and the events.
        :type reactor: :py:class:`twisted.internet.Reactor`

        :param interval: the cache flush interval. Writes will happen every interval seconds
        :type interval: int

        :param capacity: cache capacity
        :type capacity: int

        :param _clone_if_needed: *private parameter*, defaults to True, controls whether to clone
                                 transaction/blocks/metadata when returning those objects.
        :type _clone_if_needed: bool
        """
        store.remove_cache()
        self.store = store
        self.reactor = reactor
        self.interval = interval
        self.capacity = capacity
        self.flush_deferred = None
        self._clone_if_needed = _clone_if_needed
        self.cache = OrderedDict()
        # dirty_txs has the txs that have been modified but are not persisted yet
        self.dirty_txs = set()  # Set[bytes(hash)]
        self.stats = dict(hit=0, miss=0)

        # we need to use only one weakref dict, so we must first initialize super, and then
        # attribute the same weakref for both.
        super().__init__(with_index=True, with_all_index=with_all_index)
        self._tx_weakref = store._tx_weakref

    def _clone(self, x: BaseTransaction) -> BaseTransaction:
        if self._clone_if_needed:
            return x.clone()
        else:
            return x

    def pre_init(self) -> None:
        self.store.pre_init()
        self.reactor.callLater(self.interval, self._start_flush_thread)

    def _enable_weakref(self) -> None:
        super()._enable_weakref()
        self.store._enable_weakref()

    def _disable_weakref(self) -> None:
        super()._disable_weakref()
        self.store._disable_weakref()

    def _start_flush_thread(self) -> None:
        if self.flush_deferred is None:
            deferred = threads.deferToThread(self._flush_to_storage, self.dirty_txs.copy())
            deferred.addCallback(self._cb_flush_thread)
            deferred.addErrback(self._err_flush_thread)
            self.flush_deferred = deferred

    def _cb_flush_thread(self, flushed_txs: Set[bytes]) -> None:
        self.reactor.callLater(self.interval, self._start_flush_thread)
        self.flush_deferred = None

    def _err_flush_thread(self, reason: Any) -> None:
        self.log.error('error flushing transactions', reason=reason)
        self.reactor.callLater(self.interval, self._start_flush_thread)
        self.flush_deferred = None

    def _flush_to_storage(self, dirty_txs_copy: Set[bytes]) -> None:
        """Write dirty pages to disk."""
        for tx_hash in dirty_txs_copy:
            # a dirty tx might be removed from self.cache outside this thread: if _update_cache is called
            # and we need to save the tx to disk immediately. So it might happen that the tx which was
            # in the dirty set when the flush thread began is not in cache anymore, hence this `if` check
            if tx_hash in self.cache:
                tx = self._clone(self.cache[tx_hash])
                self.dirty_txs.discard(tx_hash)
                self.store._save_transaction(tx)

    def remove_transaction(self, tx: BaseTransaction) -> None:
        assert tx.hash is not None
        super().remove_transaction(tx)
        self.cache.pop(tx.hash, None)
        self.dirty_txs.discard(tx.hash)
        self._remove_from_weakref(tx)

    def save_transaction(self, tx: BaseTransaction, *, only_metadata: bool = False,
                         add_to_indexes: bool = False) -> None:
        self._save_transaction(tx)
        self._save_to_weakref(tx)

        # call super which adds to index if needed
        super().save_transaction(tx, only_metadata=only_metadata, add_to_indexes=add_to_indexes)

    def get_all_genesis(self) -> Set[BaseTransaction]:
        return self.store.get_all_genesis()

    def _save_transaction(self, tx: BaseTransaction, *, only_metadata: bool = False) -> None:
        """Saves the transaction without modifying TimestampIndex entries (in superclass)."""
        assert tx.hash is not None
        self._update_cache(tx)
        self.dirty_txs.add(tx.hash)

    def _update_cache(self, tx: BaseTransaction) -> None:
        """Updates the cache making sure it has at most the number of elements configured
        as its capacity.

        If we need to evict a tx from cache and it's dirty, write it to disk immediately.
        """
        assert tx.hash is not None
        _tx = self.cache.get(tx.hash, None)
        if not _tx:
            if len(self.cache) >= self.capacity:
                (_, removed_tx) = self.cache.popitem(last=False)
                if removed_tx.hash in self.dirty_txs:
                    # write to disk so we don't lose the last update
                    self.dirty_txs.discard(removed_tx.hash)
                    self.store.save_transaction(removed_tx)
            self.cache[tx.hash] = self._clone(tx)
        else:
            # Tx might have been updated
            self.cache[tx.hash] = self._clone(tx)
            self.cache.move_to_end(tx.hash, last=True)

    def transaction_exists(self, hash_bytes: bytes) -> bool:
        if hash_bytes in self.cache:
            return True
        return self.store.transaction_exists(hash_bytes)

    def _get_transaction(self, hash_bytes: bytes) -> BaseTransaction:
        tx: Optional[BaseTransaction]
        if hash_bytes in self.cache:
            tx = self._clone(self.cache[hash_bytes])
            self.cache.move_to_end(hash_bytes, last=True)
            self.stats['hit'] += 1
        else:
            tx = self.get_transaction_from_weakref(hash_bytes)
            if tx is not None:
                self.stats['hit'] += 1
            else:
                tx = self.store.get_transaction(hash_bytes)
                tx.storage = self
                self.stats['miss'] += 1
            self._update_cache(tx)
        self._save_to_weakref(tx)
        assert tx is not None
        return tx

    def get_all_transactions(self):
        self._flush_to_storage(self.dirty_txs.copy())
        for tx in self.store.get_all_transactions():
            tx.storage = self
            self._save_to_weakref(tx)
            yield tx

    def get_count_tx_blocks(self) -> int:
        self._flush_to_storage(self.dirty_txs.copy())
        return self.store.get_count_tx_blocks()

    def add_value(self, key: str, value: str) -> None:
        self.store.add_value(key, value)

    def remove_value(self, key: str) -> None:
        self.store.remove_value(key)

    def get_value(self, key: str) -> Optional[str]:
        return self.store.get_value(key)
