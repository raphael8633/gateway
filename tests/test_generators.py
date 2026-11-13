"""gen-service-registry.py (Caddyfile → ports, CLAUDE.md splice) and gen-index.py (cards → HTML)."""
import importlib.util
import pathlib
import tempfile
import unittest

GATEWAY = pathlib.Path(__file__).resolve().parent.parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, GATEWAY / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REG = load('gen_service_registry', 'gen-service-registry.py')
IDX = load('gen_index', 'gen-index.py')

CADDYFILE = """
(proxy_auth) {
	reverse_proxy localhost:{args[0]}
}
raphtools.com {
	handle / {
		file_server
	}
	handle /auth* {
		reverse_proxy 127.0.0.1:9091
	}
	handle /auth-admin* {
		import proxy_auth 5000
	}
	handle /reader/api* {
		route {
			import proxy_auth_strip /reader 3005
		}
	}
	handle /reader* {
		import proxy_auth 5174
	}
	handle /lib/private* {
		import proxy_auth_strip /lib 8020
	}
	handle_path /lib/* {
		reverse_proxy localhost:8020 {
			header_up -Remote-User
		}
	}
	handle {
		respond "Not Found" 404
	}
}
"""


class RegistryTest(unittest.TestCase):
    def setUp(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write(CADDYFILE)
        self.ports = REG.parse_caddyfile_ports(f.name)

    def test_ports_per_handle(self):
        self.assertEqual(self.ports['/auth'], '9091')
        self.assertEqual(self.ports['/auth-admin'], '5000')
        self.assertEqual(self.ports['/reader/api'], '3005')
        self.assertEqual(self.ports['/reader'], '5174')
        self.assertNotIn('/', self.ports)

    def test_best_port_prefers_exact_then_boundary_prefix_then_shared_children(self):
        self.assertEqual(REG.best_port('/auth-admin', self.ports), '5000')  # not /auth's 9091
        self.assertEqual(REG.best_port('/reader/', self.ports), '5174')
        self.assertEqual(REG.best_port('/lib', self.ports), '8020')        # /lib/private + /lib/ share it
        self.assertIsNone(REG.best_port('/nowhere', self.ports))

    def test_splice_replaces_only_between_markers(self):
        doc = f'head\n{REG.BEGIN}\nold\n{REG.END}\ntail\n'
        out = REG.splice(doc, '| t |')
        self.assertTrue(out.startswith('head\n') and out.endswith('tail\n'))
        self.assertIn('| t |', out)
        self.assertNotIn('old', out)
        with self.assertRaises(SystemExit):
            REG.splice('no markers here', '| t |')


class IndexTest(unittest.TestCase):
    def test_sections_follow_category_order_and_escape_html(self):
        cards = [
            {'path': '/lib', 'title': 'Lib', 'desc': 'a <b>', 'label': 'WSGI'},
            {'path': '/task-hub', 'title': 'Tasks', 'desc': 'd', 'label': 'Next.js'},
            {'path': '/zzz', 'title': 'Z', 'desc': 'd', 'label': 'Go'},
        ]
        html = IDX.render_sections(cards)
        self.assertLess(html.index('<h2>Personal</h2>'), html.index('<h2>Library</h2>'))
        self.assertLess(html.index('<h2>Library</h2>'), html.index('<h2>Other</h2>'))
        self.assertIn('a &lt;b&gt;', html)
        self.assertIn('data-path="/task-hub"', html)


if __name__ == '__main__':
    unittest.main()
