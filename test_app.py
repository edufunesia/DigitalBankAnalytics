import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test_secret_key'

@app.template_filter('date')
def format_date(value):
    """Format datetime to readable date"""
    if isinstance(value, (int, float)):
        try:
            # Convert timestamp to datetime (milliseconds)
            dt = datetime.datetime.fromtimestamp(value / 1000)
        except Exception:
            try:
                # Try as seconds if milliseconds fails
                dt = datetime.datetime.fromtimestamp(value)
            except Exception:
                # If all conversions fail, return the original value
                return str(value)
    else:
        dt = value
    
    # Format the datetime object
    try:
        return dt.strftime('%B %d, %Y') if dt else ""
    except Exception:
        # If formatting fails, return the string representation
        return str(dt) if dt else ""

@app.route('/')
def index():
    """Test homepage"""
    return "Test App Running"

@app.route('/test_date')
def test_date():
    """Test date handling"""
    # Test with different date formats
    test_dates = {
        'timestamp_ms': 1619712000000,  # April 29, 2021 in milliseconds
        'timestamp_s': 1619712000,      # April 29, 2021 in seconds
        'datetime_obj': datetime.datetime.now(),
        'string_date': 'April 29, 2021'
    }
    
    results = {}
    for key, value in test_dates.items():
        try:
            if isinstance(value, (int, float)):
                # For timestamps, try both milliseconds and seconds
                try:
                    dt_ms = datetime.datetime.fromtimestamp(value / 1000)
                    results[f"{key}_as_ms"] = dt_ms.strftime('%B %d, %Y')
                except Exception as e:
                    results[f"{key}_as_ms_error"] = str(e)
                
                try:
                    dt_s = datetime.datetime.fromtimestamp(value)
                    results[f"{key}_as_s"] = dt_s.strftime('%B %d, %Y')
                except Exception as e:
                    results[f"{key}_as_s_error"] = str(e)
            elif isinstance(value, datetime.datetime):
                # For datetime objects, just format
                results[key] = value.strftime('%B %d, %Y')
            else:
                # For strings, just return as is
                results[key] = value
        except Exception as e:
            results[f"{key}_error"] = str(e)
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5003, debug=True)
