from fastapi import UploadFile
from exmgai import Client
from src.schemas.inputs import Requirements


PROMPT = """
"""


def parse_pdf(uploads: list[UploadFile]) -> Requirements:
    
    client = Client('gpt-5.4')
    client.chat.create()

