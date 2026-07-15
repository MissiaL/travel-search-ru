import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

from scripts import api_call


class ApiCallCliTests(unittest.TestCase):
    def test_cli_accepts_patch_for_tour_actualization(self):
        argv = [
            "api_call.py",
            "--method",
            "PATCH",
            "--url",
            "https://api.botclaw.ru/travelata-partners/tours/test-id",
        ]

        with mock.patch.object(sys, "argv", argv), mock.patch.object(
            api_call, "make_request"
        ) as make_request:
            api_call.main()

        make_request.assert_called_once_with(
            "PATCH",
            "https://api.botclaw.ru/travelata-partners/tours/test-id",
            params=None,
            body=None,
            headers=None,
        )

    def test_patch_uses_timeout_longer_than_vendor_actualization(self):
        response = mock.Mock()
        response.read.return_value = b"{}"

        with mock.patch.object(api_call.urllib.request, "urlopen", return_value=response) as open_url:
            with redirect_stdout(StringIO()):
                api_call.make_request(
                    "PATCH",
                    "https://api.botclaw.ru/travelata-partners/tours/test-id",
                )

        self.assertEqual(open_url.call_args.kwargs["timeout"], 70)


if __name__ == "__main__":
    unittest.main()
