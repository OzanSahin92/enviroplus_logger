import json
import urllib.parse
import boto3
from botocore.config import Config

print("Loading function")

s3 = boto3.client("s3")


def prepare_data_timestream(data: dict) -> dict:
    record = {
        "Dimensions": [
            {"Name": "temperature", "Value": str(data["temperature"])},
            {"Name": "pressure", "Value": str(data["pressure"])},
            {"Name": "humidity", "Value": str(data["humidity"])},
            {"Name": "brightness", "Value": str(data["brightness"])},
            {"Name": "proximity", "Value": str(data["proximity"])},
            {"Name": "gas_sensor", "Value": data["gas_sensor"]},
        ],
        "MeasureName": "sensor_data",
        "MeasureValue": "1",
        "MeasureValueType": "BIGINT",
        "Time": str(int(data["timestamp"] * 1000)),
    }

    return record


def write_record_timestream(record: dict) -> None:
    # Write the record to Timestream
    # This client represents Amazon Timestream and can be used to create the database and table, and write records.
    config = Config(
        read_timeout=20, max_pool_connections=5000, retries={"max_attempts": 10}
    )
    client = boto3.client("timestream-write", config=config)
    try:
        result = client.write_records(
            DatabaseName="enviroDB", TableName="enviroTable", Records=[record]
        )
        print(
            "WriteRecords Status: " + str(result["ResponseMetadata"]["HTTPStatusCode"])
        )
    except client.exceptions.RejectedRecordsException as err:
        print("RejectedRecords: " + str(err))
        for rejected_record in err.response["RejectedRecords"]:
            print(
                "Rejected Index "
                + str(rejected_record["RecordIndex"])
                + ": "
                + rejected_record["Reason"]
            )
        print("Other records were written successfully. ")
    except Exception as err:
        print("Error:", err)


def get_s3_data(bucket: str, key: str) -> dict:
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        print("CONTENT TYPE: " + response["ContentType"])
        byte_array = response["Body"].read()
        print(byte_array)
        # Decode the bytearray to a string
        str_data = byte_array.decode("utf-8")

        # Convert the string to a dictionary
        data = json.loads(str_data)
        print(data)
        return data
    except Exception as e:
        print(e)
        print(
            "Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.".format(
                key, bucket
            )
        )
        raise e


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(
        event["Records"][0]["s3"]["object"]["key"], encoding="utf-8"
    )
    data = get_s3_data(bucket, key)
    record = prepare_data_timestream(data)
    write_record_timestream(record)
    return {"statusCode": 200}
