"""
Simple environmantal data logger using envioplus library for Enviro+ hardware
"""

import os
import sys
import time
import json
import logging
import argparse
import boto3
from smbus2 import SMBus
from bme280 import BME280
from enviroplus import gas
from botocore.exceptions import ClientError

try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559

    ltr559 = LTR559()
except ImportError:
    import ltr559


def upload_file(file_name: str, bucket: str, object_name: str = None) -> bool:
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client("s3")
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
        print(response)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def get_environmantal_data(bme280: BME280) -> dict:
    """
    Function to retrieve and store the environmantal data in a dictionary
    """
    obj_to_upload = {}
    obj_to_upload["temperature"] = bme280.get_temperature()
    obj_to_upload["pressure"] = bme280.get_pressure()
    obj_to_upload["humidity"] = bme280.get_humidity()
    obj_to_upload["brightness"] = ltr559.get_lux()
    obj_to_upload["proximity"] = ltr559.get_proximity()
    obj_to_upload["gas_sensor"] = str(gas.read_all())

    return obj_to_upload


def main(upload_interval: int) -> None:
    """
    Main Function
    """
    bus = SMBus(1)
    bme280 = BME280(i2c_dev=bus)
    file = "enviro-results.json"
    obj_to_upload = get_environmantal_data(bme280)

    try:
        while True:
            obj_to_upload["timestamp"] = time.time()
            print(obj_to_upload)

            with open(file, "w", encoding="utf-8") as fp:
                json.dump(obj_to_upload, fp)

            upload_file(file, "myenvirobucket")

            time.sleep(upload_interval)

    except KeyboardInterrupt:
        sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="python enviroplus_logger.py -u [upload interval time in seconds]"
    )

    # Add an argument
    parser.add_argument(
        "-u",
        "--uploadinterval",
        help="upload interval time of the environmental data upload",
    )

    # Parse the arguments
    args = parser.parse_args()
    main(int(args.uploadinterval))
