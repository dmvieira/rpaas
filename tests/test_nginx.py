import unittest

import mock

from rpaas.nginx import Nginx


class NginxTestCase(unittest.TestCase):

    def test_init_default(self):
        nginx = Nginx()
        self.assertEqual(nginx.nginx_reload_path, '/reload')
        self.assertEqual(nginx.nginx_dav_put_path, '/dav')
        self.assertEqual(nginx.nginx_manage_port, '8089')
        self.assertEqual(nginx.nginx_healthcheck_path, '/healthcheck')
        self.assertEqual(nginx.config_manager.location_template, """
location {path} {{
    proxy_set_header Host {host};
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_pass http://{host}:80/;
    proxy_redirect ~^http://{host}(:\d+)?/(.*)$ {path}$2;
}}
""")

    def test_init_config(self):
        nginx = Nginx({
            'NGINX_RELOAD_PATH': '/1',
            'NGINX_DAV_PUT_PATH': '/2',
            'NGINX_MANAGE_PORT': '4',
            'NGINX_LOCATION_TEMPLATE_TXT': '5',
            'NGINX_HEALTHCHECK_PATH': '6',
        })
        self.assertEqual(nginx.nginx_reload_path, '/1')
        self.assertEqual(nginx.nginx_dav_put_path, '/2')
        self.assertEqual(nginx.nginx_manage_port, '4')
        self.assertEqual(nginx.config_manager.location_template, '5')
        self.assertEqual(nginx.nginx_healthcheck_path, '6')

    @mock.patch('rpaas.nginx.requests')
    def test_init_config_location_url(self, requests):
        rsp_get = requests.get.return_value
        rsp_get.status_code = 200
        rsp_get.text = 'my result'
        nginx = Nginx({
            'NGINX_LOCATION_TEMPLATE_URL': 'http://my.com/x',
        })
        self.assertEqual(nginx.config_manager.location_template, 'my result')
        requests.get.assert_called_once_with('http://my.com/x')

    @mock.patch('rpaas.nginx.requests')
    def test_wait_healthcheck(self, requests):
        nginx = Nginx()
        count = [0]
        response = mock.Mock()
        response.status_code = 200
        response.text = 'WORKING'

        def side_effect(url, timeout):
            count[0] += 1
            if count[0] < 2:
                raise Exception('some error')
            return response

        requests.get.side_effect = side_effect
        nginx.wait_healthcheck('myhost.com', timeout=5)
        self.assertEqual(requests.get.call_count, 2)
        requests.get.assert_has_call('http://myhost.com:8089/healthcheck', timeout=2)

    @mock.patch('rpaas.nginx.requests')
    def test_wait_healthcheck_timeout(self, requests):
        nginx = Nginx()

        def side_effect(url, timeout):
            raise Exception('some error')

        requests.get.side_effect = side_effect
        with self.assertRaises(Exception):
            nginx.wait_healthcheck('myhost.com', timeout=2)
        self.assertGreaterEqual(requests.get.call_count, 2)
        requests.get.assert_has_call('http://myhost.com:8089/healthcheck', timeout=2)
