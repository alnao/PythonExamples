#!/usr/bin/env python3
"""Crea un token JWT di prova firmato con il segreto dello stack (lo legge da Secrets Manager).

uso: python3 make_token.py <ARN del segreto> [--user alberto] [--minutes 60] [--region eu-central-1]
Chiama AWS (secretsmanager:GetSecretValue) con il profilo della CLI.
"""

import argparse
import os
import sys

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lambda"))
from jwt_hs256 import sign  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="token JWT di prova per il cdk10")
    parser.add_argument("secret_arn", help="output JwtSecretArn dello stack")
    parser.add_argument("--user", default="alberto", help="utente nel claim sub")
    parser.add_argument("--minutes", type=int, default=60, help="durata del token in minuti")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION"))
    args = parser.parse_args()
    client = boto3.client("secretsmanager", region_name=args.region)
    secret = client.get_secret_value(SecretId=args.secret_arn)["SecretString"]
    print(sign({"sub": args.user}, secret, args.minutes))


if __name__ == "__main__":
    main()
