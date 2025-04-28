import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")

# Import all the modules used in analysis.py
import logging
import pandas as pd
import numpy as np
import re
import string
import nltk
import threading
import time
from queue import Queue
from textblob import TextBlob
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# Import the app
from app import app

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
