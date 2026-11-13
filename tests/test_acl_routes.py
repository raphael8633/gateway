"""Every Authelia ACL rule must be reachable from a forward_auth route in the Caddyfile.

Authelia only evaluates paths that Caddy sends through `auth_portal` (directly or via
proxy_auth / proxy_auth_strip). A rule for a path Caddy serves without forward_auth,
or for a path Caddy does not route at all, is dead and only misleads the reader.
"""
import pathlib
import re
import unittest

GATEWAY = pathlib.Path(__file__).resolve().parent.parent
CADDYFILE = GATEWAY / 'Caddyfile'
AUTHELIA = GATEWAY.parent / 'global-auth' / 'config' / 'configuration.yml'
GATED = re.compile(r'import\s+(auth_portal|proxy_auth|proxy_auth_strip)\b')


def gated_handles(src):
    """Path matchers of handle blocks whose body imports the auth gate."""
    out = []
    for m in re.finditer(r'^\s*handle(?:_path)?\s+(\S+)\s*\{', src, re.MULTILINE):
        depth, j = 1, m.end()
        while j < len(src) and depth:
            depth += {'{': 1, '}': -1}.get(src[j], 0)
            j += 1
        if GATED.search(src[m.end():j]):
            out.append(m.group(1))
    return out


def sample_path(matcher):
    """A concrete request path a Caddy path matcher accepts."""
    return matcher.rstrip('*') if matcher.endswith('*') else matcher


def acl_resources(src):
    return re.findall(r'^\s*-\s+(\^\S+)\s*$', src, re.MULTILINE)


class AclRouteTest(unittest.TestCase):
    @unittest.skipUnless(AUTHELIA.exists(), 'global-auth checkout not present')
    def test_every_acl_matches_a_gated_route(self):
        paths = [sample_path(h) for h in gated_handles(CADDYFILE.read_text())]
        self.assertIn('/', paths)
        dead = [r for r in acl_resources(AUTHELIA.read_text())
                if not any(re.match(r, p) or re.match(r, p + '/') for p in paths)]
        self.assertEqual(dead, [], f'ACL rules no gated Caddy route can reach: {dead}')


if __name__ == '__main__':
    unittest.main()
