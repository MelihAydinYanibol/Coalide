import unittest
from unittest.mock import Mock, patch

import requests

from parental_connection import get_pending_exceptional_time


class GetPendingExceptionalTimeTests(unittest.TestCase):
    @patch("parental_connection.requests.get")
    def test_sums_matching_pending_exception_times(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "items": [
                    {
                        "method": "POST",
                        "endpoint": "/exceptions",
                        "data": {
                            "app_name": "OVERALL",
                            "date": "2026-05-23",
                            "exception_time": 120,
                            "reason": "5 Doğru yaptığınız için - COALIDE",
                        },
                    },
                    {
                        "method": "POST",
                        "endpoint": "/exceptions",
                        "data": "{\"app_name\":\"OVERALL\",\"date\":\"2026-05-23\",\"exception_time\":60,\"reason\":\"COALIDE queued\"}",
                    },
                    {
                        "method": "POST",
                        "endpoint": "/exceptions",
                        "data": {
                            "app_name": "OVERALL",
                            "date": "2026-05-23",
                            "exception_time": 999,
                            "reason": "Manual bonus",
                        },
                    },
                    {
                        "method": "POST",
                        "endpoint": "/exceptions",
                        "data": {
                            "app_name": "discord.exe",
                            "date": "2026-05-23",
                            "exception_time": 500,
                            "reason": "COALIDE",
                        },
                    },
                ]
            },
        }
        mock_get.return_value = mock_response

        total_pending = get_pending_exceptional_time(
            "http://pcv2.local:5005",
            "OVERALL",
            "2026-05-23",
            "COALIDE",
        )

        self.assertEqual(total_pending, 180)

    @patch("parental_connection.requests.get")
    def test_returns_zero_on_non_200(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        total_pending = get_pending_exceptional_time(
            "http://pcv2.local:5005", "OVERALL", "2026-05-23", "COALIDE"
        )

        self.assertEqual(total_pending, 0)

    @patch(
        "parental_connection.requests.get",
        side_effect=requests.exceptions.RequestException("network down"),
    )
    def test_returns_zero_on_request_error(self, _mock_get):
        total_pending = get_pending_exceptional_time(
            "http://pcv2.local:5005", "OVERALL", "2026-05-23", "COALIDE"
        )

        self.assertEqual(total_pending, 0)


if __name__ == "__main__":
    unittest.main()
