"""Health endpoint + service tests (no network, in-process)."""
import unittest

from fastapi.testclient import TestClient

from server.main import app
from server.services.health import health_status


class HealthTests(unittest.TestCase):
    def test_service(self):
        self.assertEqual(health_status(), {"status": "ok", "api_version": "1"})

    def test_endpoint_200_and_body(self):
        with TestClient(app) as client:
            r = client.get("/v1/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "api_version": "1"})
        self.assertTrue(r.headers["content-type"].startswith("application/json"))

    def test_wrong_method_and_path(self):
        with TestClient(app) as client:
            self.assertEqual(client.post("/v1/health").status_code, 405)
            self.assertEqual(client.get("/v1/nope").status_code, 404)


if __name__ == "__main__":
    unittest.main()
