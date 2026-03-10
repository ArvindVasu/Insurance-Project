
import streamlit as st
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List
from langchain_core.runnables import Runnable
from serpapi import GoogleSearch
from vanna.remote import VannaDefault
from docx import Document
import tempfile
import os
from dotenv import load_dotenv
import json
import re
from openai import OpenAI
import pandas as pd
import sqlite3
from typing import Optional, List, Dict, Any, Tuple
import matplotlib.pyplot as plt
import networkx as nx
from io import BytesIO
from datetime import datetime
import json
from datetime import date, timedelta
from pptx import Presentation
from pptx.util import Inches, Pt
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
import tempfile
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.table import Table as DocxTable
import tempfile
import uuid
from docx.table import Table as DocxTable
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import numpy as np
from pathlib import Path
from io import BytesIO
import base64
from time import sleep
from urllib.parse import urlparse
import io
import re
from difflib import get_close_matches
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
import math
import logging

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_llm(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            # model="gpt-3.5-turbo",
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an intelligent AI assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI call failed: {e}"
