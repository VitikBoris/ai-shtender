#!/usr/bin/env python3
"""
Zip build dir and upload to Yandex Object Storage.
Prints SHA256 of the archive (for yc serverless function version create --package-sha256).

Usage:
  set AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
  python scripts/upload_package.py --build-dir .yc/build --bucket BUCKET [--key deploy/package.zip]
"""
import argparse
import hashlib
import os
import sys
import zipfile

try:
    import boto3
except ImportError:
    print("boto3 required: pip install boto3", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Zip build dir and upload to Yandex Object Storage")
    parser.add_argument("--build-dir", required=True, help="Path to build directory")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--key", default="deploy/package.zip", help="Object key in bucket")
    parser.add_argument("--endpoint", default="https://storage.yandexcloud.net", help="S3 endpoint URL")
    args = parser.parse_args()

    build_dir = os.path.abspath(args.build_dir)
    if not os.path.isdir(build_dir):
        print("Error: not a directory:", build_dir, file=sys.stderr)
        sys.exit(1)

    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        print("Error: set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY", file=sys.stderr)
        sys.exit(1)

    zip_path = os.path.join(os.path.dirname(build_dir), "package.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(build_dir):
            for f in files:
                path = os.path.join(root, f)
                arcname = os.path.relpath(path, build_dir)
                zf.write(path, arcname)

    with open(zip_path, "rb") as f:
        zip_sha256 = hashlib.sha256(f.read()).hexdigest()

    try:
        client = boto3.client(
            "s3",
            region_name="ru-central1",
            endpoint_url=args.endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        with open(zip_path, "rb") as f:
            client.upload_fileobj(f, args.bucket, args.key)
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass

    print(zip_sha256)


if __name__ == "__main__":
    main()
