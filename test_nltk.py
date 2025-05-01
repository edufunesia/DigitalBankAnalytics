import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")

try:
    import nltk
    print(f"NLTK version: {nltk.__version__}")
    print("NLTK imported successfully")
except ImportError as e:
    print(f"Error importing NLTK: {e}")

try:
    import textblob
    print("TextBlob imported successfully")
except ImportError as e:
    print(f"Error importing TextBlob: {e}")

try:
    from textblob import TextBlob
    print("TextBlob.TextBlob imported successfully")
except ImportError as e:
    print(f"Error importing TextBlob.TextBlob: {e}")

try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    print("Sastrawi.Stemmer.StemmerFactory imported successfully")
except ImportError as e:
    print(f"Error importing Sastrawi.Stemmer.StemmerFactory: {e}")

try:
    from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
    print("Sastrawi.StopWordRemover.StopWordRemoverFactory imported successfully")
except ImportError as e:
    print(f"Error importing Sastrawi.StopWordRemover.StopWordRemoverFactory: {e}")

# Try to import all the modules used in analysis.py
try:
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
    print("All modules imported successfully")
except ImportError as e:
    print(f"Error importing modules: {e}")
