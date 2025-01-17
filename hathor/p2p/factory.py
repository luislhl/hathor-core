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

from typing import TYPE_CHECKING, Optional, Type

from twisted.internet import protocol
from twisted.internet.interfaces import IAddress

from hathor.p2p.manager import ConnectionsManager
from hathor.p2p.peer_id import PeerId
from hathor.p2p.protocol import HathorLineReceiver

if TYPE_CHECKING:
    from hathor.manager import HathorManager  # noqa: F401

MyServerProtocol = HathorLineReceiver
MyClientProtocol = HathorLineReceiver


class HathorServerFactory(protocol.ServerFactory):
    """ HathorServerFactory is used to generate HathorProtocol objects when a new connection arrives.
    """

    manager: Optional[ConnectionsManager]
    protocol: Optional[Type[MyServerProtocol]] = MyServerProtocol

    def __init__(
            self,
            network: str,
            my_peer: PeerId,
            connections: Optional[ConnectionsManager] = None,
            *,
            node: 'HathorManager',
            use_ssl: bool,
    ):
        super().__init__()
        self.network = network
        self.my_peer = my_peer
        self.connections = connections
        self.node = node
        self.use_ssl = use_ssl

    def buildProtocol(self, addr: IAddress) -> MyServerProtocol:
        assert self.protocol is not None
        p = self.protocol(
            network=self.network,
            my_peer=self.my_peer,
            connections=self.connections,
            node=self.node,
            use_ssl=self.use_ssl,
            inbound=True,
        )
        p.factory = self
        return p


class HathorClientFactory(protocol.ClientFactory):
    """ HathorClientFactory is used to generate HathorProtocol objects when we connected to another peer.
    """

    manager: Optional[ConnectionsManager]
    protocol: Optional[Type[MyClientProtocol]] = MyClientProtocol

    def __init__(
            self,
            network: str,
            my_peer: PeerId,
            connections: Optional[ConnectionsManager] = None,
            *,
            node: 'HathorManager',
            use_ssl: bool,
    ):
        super().__init__()
        self.network = network
        self.my_peer = my_peer
        self.connections = connections
        self.node = node
        self.use_ssl = use_ssl

    def buildProtocol(self, addr: IAddress) -> MyClientProtocol:
        assert self.protocol is not None
        p = self.protocol(
            network=self.network,
            my_peer=self.my_peer,
            connections=self.connections,
            node=self.node,
            use_ssl=self.use_ssl,
            inbound=False,
        )
        p.factory = self
        return p
