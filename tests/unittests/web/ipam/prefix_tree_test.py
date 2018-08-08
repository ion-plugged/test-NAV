import unittest
from nav.web.ipam.prefix_tree import make_tree_from_ip

# TODO: Mock prefixes via fixtures?


class PrefixTreeTest(unittest.TestCase):
    def test_prefix_tree_invalid_cidr(self):
        cidrs = ["192.168.1.1/42"]
        self.assertRaises(ValueError, make_tree_from_ip, cidrs)

    def test_prefix_tree_valid_cidr(self):
        cidrs = ["10.0.0.0/16", "10.0.1.0/24"]
        tree = make_tree_from_ip(cidrs)
        # sanity check: tree root should have children
        self.assertTrue(tree.children_count > 0)
        # sanity check: spanned prefix should be within spanning prefix
        child = tree.children[0].children[0]
        self.assertEqual(child.prefix, "10.0.1.0/24")
        self.assertEqual(child.prefixlen, 24)
