import nltk
import sys

def test_punkt_tokenizer():
    """Test NLTK's punkt tokenizer functionality"""
    try:
        # Check if punkt data is available
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Punkt tokenizer data not found. Downloading...")
        nltk.download('punkt')
    
    # Sample text for testing
    sample_text = "This is a test sentence. It contains multiple sentences! Does it work?"
    
    # Tokenize sentences
    sentences = nltk.sent_tokenize(sample_text)
    print(f"Tokenized sentences: {sentences}")
    
    # Tokenize words
    words = nltk.word_tokenize(sample_text)
    print(f"Tokenized words: {words}")
    
    return len(sentences) > 1 and len(words) > 5

if __name__ == "__main__":
    success = test_punkt_tokenizer()
    if success:
        print("Punkt tokenizer test passed successfully!")
        sys.exit(0)
    else:
        print("Punkt tokenizer test failed!")
        sys.exit(1)