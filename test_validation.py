import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Provide a mock boto3 module for local testing
os.environ["OUTPUT_BUCKET"] = "test-output-bucket"
sys.modules["boto3"] = MagicMock()

import lambda_function


class TestInputValidation(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.context.aws_request_id = "local-test-123"

    def test_missing_s3_details(self):
        event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "s3": {
                        "bucket": {"name": "test-bucket"}
                    }
                }
            ]
        }

        with self.assertRaisesRegex(ValueError, "missing object details"):
            lambda_function.lambda_handler(event, self.context)

    def test_unsupported_file_type(self):
        event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "report.pdf"}
                    }
                }
            ]
        }

        with self.assertRaisesRegex(ValueError, "Unsupported file type"):
            lambda_function.lambda_handler(event, self.context)

    @patch.object(lambda_function, "s3")
    def test_invalid_utf8_file(self, mock_s3):
        mock_s3.get_object.return_value = {
            "Body": MagicMock()
        }

        mock_s3.get_object.return_value["Body"].read.return_value = b"\xff\xfe"

        event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "report.txt"}
                    }
                }
            ]
        }

        with self.assertRaisesRegex(ValueError, "Invalid file encoding"):
            lambda_function.lambda_handler(event, self.context)

    def test_empty_event(self):
        result = lambda_function.lambda_handler({}, self.context)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(result["body"], "No files to process")

    @patch.object(lambda_function, "s3")
    def test_valid_text_file(self, mock_s3):
        mock_body = MagicMock()
        mock_body.read.return_value = (
            b"Name: Jordan Lee\n"
            b"Department: Cloud Operations\n"
            b"Skills: AWS, Python, Linux"
        )

        mock_s3.get_object.return_value = {
            "Body": mock_body
        }

        event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "s3": {
                        "bucket": {"name": "test-input-bucket"},
                        "object": {"key": "employee.txt"}
                    }
                }
            ]
        }

        result = lambda_function.lambda_handler(
            event, self.context
        )

        self.assertEqual(result["statusCode"], 200)

        mock_s3.put_object.assert_called_once()

        uploaded_report = mock_s3.put_object.call_args.kwargs

        report = json.loads(
            uploaded_report["Body"].decode("utf-8")
        )

        self.assertEqual(report["line_count"], 3)
        self.assertEqual(report["word_count"], 10)
        self.assertEqual(report["status"], "SUCCESS")



if __name__ == "__main__":
    unittest.main(verbosity=2)
