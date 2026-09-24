import os
from pathlib import Path

import openstack
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def get_conn():
    return openstack.connect(
        auth_url=os.environ["OS_AUTH_URL"],
        username=os.environ["OS_USERNAME"],
        password=os.environ["OS_PASSWORD"],
        project_name=os.environ["OS_PROJECT_NAME"],
        user_domain_name=os.environ["OS_USER_DOMAIN_NAME"],
        project_domain_name=os.environ["OS_PROJECT_DOMAIN_NAME"],
        region_name=os.environ["OS_REGION_NAME"],
        interface=os.environ["OS_INTERFACE"],
        compute_api_version=os.environ["OS_COMPUTE_API_VERSION"],
    )