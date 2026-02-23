from services.llm_service import call_llm


import streamlit as st
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List
from langchain_core.runnables import Runnable
from serpapi import GoogleSearch
from vanna.remote import VannaDefault
from dotenv import load_dotenv
import json
import re
from openai import OpenAI
import pandas as pd
import sqlite3

import matplotlib.pyplot as plt
import networkx as nx
from io import BytesIO
from datetime import datetime
import json
from datetime import date, timedelta
from pptx import Presentation
from pptx.util import Inches, Pt
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

def generate_follow_up_questions(user_prompt: str) -> List[str]:
    followup_prompt = f"""
    Based on the following insurance-related user query:
    "{user_prompt}"

    Suggest 3 intelligent follow-up questions the user could ask next. Keep them short, relevant, and not repetitive.
    Return them as a plain list.
    """
    try:
        response = call_llm(followup_prompt)
        return re.findall(r"^\s*[-–•]?\s*(.+)", response, re.MULTILINE)[:3] or response.split("\n")[:3]
    except:
        return []