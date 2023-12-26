"""
Simple environmantal data logger using envioplus library for Enviro+ hardware
"""

import os
import sys
import time
import json
import boto3
import logging
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


def upload_file(file_name, bucket, object_name=None):
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


obj_to_upload = {}

bus = SMBus(1)
bme280 = BME280(i2c_dev=bus)

try:
    while True:
        timestamp = time.time()
        obj_to_upload["timestamp"] = timestamp

        obj_to_upload["temperature"] = bme280.get_temperature()
        obj_to_upload["pressure"] = bme280.get_pressure()
        obj_to_upload["humidity"] = bme280.get_humidity()

        obj_to_upload["brightness"] = ltr559.get_lux()
        obj_to_upload["proximity"] = ltr559.get_proximity()

        gas_readings = gas.read_all()
        obj_to_upload["gas_sensor"] = str(gas_readings)

        print(obj_to_upload)
        file = "enviro-results.json"
        with open(file, "w") as fp:
            json.dump(obj_to_upload, fp)

        upload_file("enviro-results.json", "myenvirobucket")

except KeyboardInterrupt:
    sys.exit
