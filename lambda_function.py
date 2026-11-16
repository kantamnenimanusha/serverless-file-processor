
import json
import os
import boto3
import logging

from urllib.parse import unquote_plus
from pathlib import PurePosixPath

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create the S3 client outside the handler
s3 = boto3.client("s3")

OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]


def lambda_handler(event, context):

    logger.info("Serverless File Processor started!")
    logger.info("Request ID: %s", context.aws_request_id)

    # Validate the incoming event
    if not isinstance(event, dict):
        raise ValueError("Invalid event: expected a dictionary.")

    records = event.get("Records", [])

    if not records:
        logger.warning("No S3 records found. Nothing to process.")
        return {
            "statusCode": 200,
            "body": "No files to process"
        }

    if not isinstance(records, list):
        raise ValueError("Invalid event: Records must be a list.")

    for record in records:

        if not isinstance(record, dict):
            raise ValueError("Invalid S3 record: expected a dictionary.")

        if record.get("eventSource") != "aws:s3":
            logger.warning("Ignoring non-S3 event")
            continue

        try:
            # Validate S3 event structure
            s3_info = record.get("s3")

            if not isinstance(s3_info, dict):
                raise ValueError("Invalid S3 event: missing S3 details.")

            bucket_info = s3_info.get("bucket")
            object_info = s3_info.get("object")

            if not isinstance(bucket_info, dict):
                raise ValueError("Invalid S3 event: missing bucket details.")

            if not isinstance(object_info, dict):
                raise ValueError("Invalid S3 event: missing object details.")

            input_bucket = bucket_info.get("name")
            encoded_key = object_info.get("key")

            if not input_bucket or not encoded_key:
                raise ValueError("Invalid S3 event: bucket name or object key is missing.")

            # Decode URL-encoded S3 object key
            file_key = unquote_plus(encoded_key)

            logger.info("Input bucket: %s", input_bucket)
            logger.info("File name: %s", file_key)

            # Validate file extension
            if not file_key.lower().endswith(".txt"):
                raise ValueError(
                    "Unsupported file type. Only .txt files are accepted."
                )

            # Download the uploaded file
            response = s3.get_object(
                Bucket=input_bucket,
                Key=file_key
            )

            # Decode file content
            try:
                file_content = response["Body"].read().decode("utf-8")
            except UnicodeDecodeError as error:
                raise ValueError(
                    "Invalid file encoding. Expected UTF-8 text."
                ) from error

            # Analyse file content
            line_count = len(file_content.splitlines())
            word_count = len(file_content.split())

            # Generate JSON report
            report = {
                "source_file": PurePosixPath(file_key).name,
                "input_bucket": input_bucket,
                "input_key": file_key,
                "line_count": line_count,
                "word_count": word_count,
                "status": "SUCCESS"
            }

            # Create output filename
            output_key = f"processed/{file_key}.json"

            # Upload report to output bucket
            s3.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=output_key,
                Body=json.dumps(report, indent=4).encode("utf-8"),
                ContentType="application/json"
            )

            logger.info("Processing completed successfully!")
            logger.info("Report location: %s", output_key)
            logger.info("Report: %s", json.dumps(report))

        except Exception:
            logger.exception(
                "Failed to process S3 record. "
                "The Lambda invocation will report a failure."
            )
            raise

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "File processing completed successfully"
        })
    }
