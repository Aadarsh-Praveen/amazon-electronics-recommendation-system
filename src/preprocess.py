import re
import pandas as pd

# CLEAN TEXT
def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'<.*?>', ' ', text)                           # remove HTML tags
    text = re.sub(r'(http|https)://\S+', ' ', text)              # remove URLs
    text = re.sub(r'[^a-z0-9\s]', ' ', text)                     # remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()                     # normalize spaces
    return text

    
# FLATTEN STYLE FIELD
def flatten_style(style_obj):
    if isinstance(style_obj, dict):
        try:
            return list(style_obj.values())[0]
        except:
            return None
    return None
