from django.test import SimpleTestCase
from django.urls import resolve


class UrlSmokeTests(SimpleTestCase):
    def test_health_route_exists(self):
        self.assertEqual(resolve('/api/health').url_name, 'health')

    def test_auth_routes_exist(self):
        self.assertEqual(resolve('/api/auth/register').url_name, 'register')
        self.assertEqual(resolve('/api/auth/login').url_name, 'login')

    def test_analysis_routes_exist(self):
        self.assertEqual(resolve('/api/analyze').url_name, 'analyze')
        self.assertEqual(resolve('/api/analysis/history').url_name, 'history')