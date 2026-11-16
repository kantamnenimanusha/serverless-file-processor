
import json
import os
import boto3
from urllib.parse import unquote_plus
from pathlib import PurePosixPath

# Create the S3 client outside the handler.
# AWS can reuse it across warm Lambda invocations.
s3 = boto3.client("s3")

OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]


def lambda_handler(event, context):

    print("Serverless File Processor started!")
    print("Request ID:", context.aws_request_id)

    records = event.get("Records", [])

    if not records:
        print("No S3 records found. Nothing to process.")
        return {
            "statusCode": 200,
            "body": "No files to process"
        }

    for record in records:

        if record.get("eventSource") != "aws:s3":
            print("Ignoring non-S3 event")
            continue

        # Extract input bucket and object key
        input_bucket = record["s3"]["bucket"]["name"]
        file_key = unquote_plus(record["s3"]["object"]["key"])

        print("Input bucket:", input_bucket)
        print("File name:", file_key)

        # Download the uploaded file
        response = s3.get_object(
            Bucket=input_bucket,
            Key=file_key
        )

        file_content = response["Body"].read().decode("utf-8")

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

        print("Processing completed!")
        print("Report location:", output_key)
        print("Report:", json.dumps(report))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "File processing completed successfully"
        })
    }
