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

logging.basicConfig(
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def upload_file(
    file_name: str, bucket: str, current_time: float, object_name: str = None
) -> bool:
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param current_time: Current time in seconds since epoch 1970
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = str(current_time) + "_" + os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client("s3")
    try:
        s3_client.upload_file(file_name, bucket, object_name)
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


def main(upload_interval: int, file: str) -> None:
    """
    Main Function
    """
    bus = SMBus(1)
    bme280 = BME280(i2c_dev=bus)

    logging.info("Getting environmental data")
    obj_to_upload = get_environmantal_data(bme280)

    try:
        while True:
            current_time = time.time()
            obj_to_upload["timestamp"] = current_time
            logging.info("Environmental data: %s", obj_to_upload)
            logging.info("Persisting data temporarily in %s", file)
            with open(file, "w", encoding="utf-8") as fp:
                json.dump(obj_to_upload, fp)
            logging.info("Uploading data to AWS s3")
            upload_file(file, "myenvirobucket", current_time)
            logging.info("Waiting for %d s", upload_interval)
            time.sleep(upload_interval)

    except KeyboardInterrupt:
        logging.info("Got KeyboardInterrupt")
        sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simple logger of environmental data with Enviro+ hardware"
    )

    # Add an argument
    parser.add_argument(
        "-u",
        "--uploadinterval",
        help="upload interval time of the environmental data upload",
    )
    parser.add_argument(
        "-f", "--file", help="temporary file to persist environmental data"
    )

    # Parse the arguments
    args = parser.parse_args()
    main(int(args.uploadinterval), args.file)
