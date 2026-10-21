from django.test import TestCase, Client
from django.urls import reverse


class HealthCheckTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check_endpoint_returns_200_and_json(self):
        """Verify GET /api/health/ returns status 200 and reports database connected."""
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("database"), "connected")
        self.assertEqual(data.get("engine"), "postgresql")
