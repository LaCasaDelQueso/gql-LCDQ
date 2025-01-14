ENVIRONMENTS = ["staging", "production"]
VAULT_S3_BUCKET = {env: "alima-{}-vault".format(env) for env in ENVIRONMENTS}


def get_envs(cfg) -> list:
    env = []
    extra_mappings = {
        "ALIMA_APPNAME": cfg.get_parameter("name"),
        "ALIMA_ENVIRONMENT": cfg.environment,
        "ALIMA_LABEL": cfg.label or "",
        "ALIMA_VAULT": VAULT_S3_BUCKET.get(cfg.environment, ""),
        "appname": cfg.get_parameter("name"),
        "environment": cfg.environment,
    }
    for key, value in list(extra_mappings.items()):
        if value is not None:
            env.append({"name": key, "value": value})
    return env
