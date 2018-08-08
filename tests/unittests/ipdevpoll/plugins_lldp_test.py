from nav.ipdevpoll.plugins.lldp import LLDP
from nav.ipdevpoll.storage import ContainerRepository

from mock import Mock


def test_non_ascii_chassis_id_should_not_crash():
    record = Mock(chassid_id='a\x9enon-ascii')
    plugin = LLDP(None, None, ContainerRepository())
    plugin._store_unidentified(record)
