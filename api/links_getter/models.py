import json
from pydantic import BaseModel, Field, validator
from pathlib import Path



class DocInfo(BaseModel):
    doc_id:str
    tags: list[str] = None
    author: str = None
    date: str = None
    url: str = None