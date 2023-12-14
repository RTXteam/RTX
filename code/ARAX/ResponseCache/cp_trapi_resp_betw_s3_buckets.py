#!/usr/bin/env python3

import argparse
import boto3


def _get_args() -> argparse.Namespace:
    arg_parser = \
        argparse.ArgumentParser(description="cp_trapi_resp_betw_s3_buckets.py:"
                                " copy TRAPI response JSON file(s) from on S3 "
                                "bucket to another S3 bucket")
    arg_parser.add_argument('--aws_profile',
                            help="the AWS profile to use",
                            default='default')
    arg_parser.add_argument('--verbose',
                            default=False,
                            action='store_true')
    arg_parser.add_argument('src_bucket',
                            help="the source bucket URL")
    arg_parser.add_argument('dst_bucket',
                            help="the destination bucket URL")
    arg_parser.add_argument('response_ids',
                            type=int,
                            nargs='+',
                            help="the ARAX Response IDs of the JSON files to "
                            "copy")
    return arg_parser.parse_args()


if __name__ == "__main__":
    args = _get_args()
    src_bucket = args.src_bucket
    dst_bucket = args.dst_bucket
    resp_ids = args.response_ids
    boto3_session = boto3.session.Session(profile_name=args.aws_profile)
    rsrc = boto3_session.resource("s3")
    for resp_id in resp_ids:
        obj_name = str(resp_id) + '.json'
        copy_source = {'Bucket': src_bucket,
                       'Key': obj_name}
        src_url = src_bucket + '/' + obj_name
        rsrc.meta.client.copy(copy_source, dst_bucket, obj_name)
        if args.verbose:
            print(f"s3://{src_bucket}/{obj_name} => "
                  f"s3://{dst_bucket}/{obj_name}")
