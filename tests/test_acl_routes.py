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


def matching_variant(rule, path):
    """The form of `path` (bare or with a trailing slash) that `rule` matches, or None."""
    for p in (path, path + '/'):
        if re.match(rule, p):
            return p
    return None


@unittest.skipUnless(AUTHELIA.exists(), 'global-auth checkout not present')
class AclRouteTest(unittest.TestCase):
    def setUp(self):
        self.paths = [sample_path(h) for h in gated_handles(CADDYFILE.read_text())]
        self.rules = acl_resources(AUTHELIA.read_text())

    def test_every_acl_matches_a_gated_route(self):
        self.assertIn('/', self.paths)
        dead = [r for r in self.rules if not any(matching_variant(r, p) for p in self.paths)]
        self.assertEqual(dead, [], f'ACL rules no gated Caddy route can reach: {dead}')

    def test_every_gated_route_has_an_acl_rule(self):
        # default_policy is deny: a forward_auth route with no rule answers 403, not 302 /auth.
        uncovered = [p for p in self.paths if not any(matching_variant(r, p) for r in self.rules)]
        self.assertEqual(uncovered, [], f'gated Caddy routes without an Authelia ACL rule: {uncovered}')

    def test_acl_rules_accept_a_query_string(self):
        # Authelia matches the rule against path+query: `^/app$` lets /app in and 403s /app?x=1.
        broken = []
        for r in self.rules:
            for p in self.paths:
                v = matching_variant(r, p)
                if v and not re.match(r, v + '?x=1'):
                    broken.append(f'{r} rejects {v}?x=1')
        self.assertEqual(broken, [], f'ACL rules that drop requests carrying a query string: {broken}')


if __name__ == '__main__':
    unittest.main()
