import os
import boto3
import logging

s3 = boto3.resource('s3')

ENV = os.getenv("ENV", "dev")
APP = os.getenv("APP_NAME", "gqlapi")
ENVIRONMENTS = ["staging", "production"]
VAULT_S3_BUCKET = {env: "alima-vault-{}".format(env) for env in ENVIRONMENTS}


def set_vault_vars():
    logging.info("Setting vault variables")
    vault_vars = get_envs_from_vault()
    for key, val in vault_vars.items():
        os.environ[key] = val


def get_envs_from_vault():
    """ Download env vars from s3 vault and return a dict
        of var names and value
    """
    if get_env() == "local" or get_env() == "development":
        return {}
    vault_name = VAULT_S3_BUCKET[get_env()]
    vault_bucket = s3.Bucket(vault_name)  # type: ignore
    prefix = "{}/".format(APP)
    vault_vars = {}
    for object in vault_bucket.objects.filter(Prefix=prefix):
        keyname = object.key.split("/")
        if len(keyname) < 2 or keyname[-1] == "":
            continue
        body = object.get()['Body'].read().decode()
        logging.info("Setting: {}".format(keyname[-1]))
        vault_vars[keyname[-1]] = body
    return vault_vars


def get_env():
    if ENV.lower() in set(['dev', 'development']):
        return 'development'
    elif ENV.lower() in set(['stg', 'staging']):
        return 'staging'
    elif ENV.lower() in set(['prod', 'production']):
        return 'production'
    else:
        return 'local'
