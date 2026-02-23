
from vanna.remote import VannaDefault
from config.global_variables import DB_PATH
import os
from dotenv import load_dotenv

load_dotenv()


def vanna_configure():
    vanna_api_key = os.getenv("vanna_api_key")
    vanna_model_name = os.getenv("vanna_model_name")

    if not vanna_api_key or not vanna_model_name:
        raise ValueError("Vanna configuration missing. Set vanna_api_key and vanna_model_name in .env")

    vn_model = VannaDefault(model=vanna_model_name, api_key=vanna_api_key)
    vn_model.connect_to_sqlite(DB_PATH)
    return vn_model

