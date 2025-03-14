from flask import Flask, request, jsonify, make_response, render_template
from flask_cors import CORS
import torch
from transformers import T5Tokenizer, T5ForConditionalGeneration, T5Config
from youtube_transcript_api import YouTubeTranscriptApi
import traceback
import json
import logging
import sys
from werkzeug.exceptions import HTTPException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Simplify CORS setup
CORS(app)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Load the model and tokenizer
try:
    # Load config from local config directory
    config = T5Config.from_pretrained("./config")
    
    # Initialize model with config and load weights
    model = T5ForConditionalGeneration(config)
    model.load_state_dict(torch.load("summarizer.pth", map_location=torch.device('cpu')))
    
    # Load tokenizer from local tokenizer directory
    tokenizer = T5Tokenizer.from_pretrained("./tokenizer")
    
    model.eval()
except Exception as e:
    print(f"Error loading model: {str(e)}")
    raise

def chunk_text(text, chunk_size=512):
    """Splits text into chunks of a given size (tokens)."""
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

def summarize_chunk(chunk):
    """Summarizes a single text chunk using the T5 model."""
    inputs = tokenizer("summarize: " + chunk, return_tensors="pt", max_length=512, truncation=True)
    
    text_length = len(chunk.split())
    max_summary_length = min(300, text_length // 2)
    min_summary_length = min(120, max_summary_length // 2)

    summary_ids = model.generate(
        inputs.input_ids, 
        max_length=max_summary_length, 
        min_length=min_summary_length, 
        length_penalty=2.0, 
        num_beams=4
    )
    
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

def summarize_large_text(text):
    """Splits text into chunks, summarizes each chunk, and joins the summaries."""
    chunks = chunk_text(text, chunk_size=300)
    summaries = [summarize_chunk(chunk) for chunk in chunks]
    return " ".join(summaries)

def get_youtube_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ' '.join([t['text'] for t in transcript_list])
        logger.info("\n=== TRANSCRIPT ===")
        logger.info(transcript)
        logger.info("=== END TRANSCRIPT ===\n")
        return transcript
    except Exception as e:
        logger.error(f"Transcript error for video {video_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return None

@app.errorhandler(Exception)
def handle_error(e):
    logger.error(f"Unhandled error: {str(e)}")
    logger.error(traceback.format_exc())
    
    if isinstance(e, HTTPException):
        response = jsonify({
            'error': str(e),
            'status_code': e.code
        })
        response.status_code = e.code
    else:
        response = jsonify({
            'error': str(e),
            'status_code': 500
        })
        response.status_code = 500
    
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize-youtube', methods=['POST'])
def summarize_youtube():
    try:
        logger.info("\n=== NEW REQUEST ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request data: {request.get_data(as_text=True)}")
        
        if not request.is_json:
            return jsonify({
                'error': 'Request must be JSON',
                'content_type': request.headers.get('Content-Type')
            }), 400

        data = request.get_json()
        logger.info(f"Parsed JSON data: {data}")
        
        if not data:
            response = jsonify({
                'error': 'No data provided'
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
            
        video_id = data.get('video_id', '')
        logger.info(f"Video ID: {video_id}")
        
        if not video_id:
            logger.warning("No video ID provided")
            response = jsonify({
                'error': 'No video ID provided'
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        # Get transcript
        logger.info(f"\nFetching transcript for video ID: {video_id}")
        transcript = get_youtube_transcript(video_id)
        if not transcript:
            logger.error("Failed to get transcript")
            response = jsonify({
                'error': 'Could not get transcript for this video'
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        # Summarize
        try:
            logger.info("\nGenerating summary...")
            summary = summarize_large_text(transcript)
            logger.info("\n=== SUMMARY ===")
            logger.info(summary)
            logger.info("=== END SUMMARY ===\n")
            
            response_data = {
                'success': True,
                'summary': summary,
                'original_length': len(transcript.split()),
                'summary_length': len(summary.split())
            }
            logger.info(f"\nSending response: {json.dumps(response_data, indent=2)}")
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
            
        except Exception as e:
            error_msg = f"Summarization error: {str(e)}"
            logger.error(f"\nError: {error_msg}")
            logger.error(traceback.format_exc())
            response = jsonify({
                'error': error_msg
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 500
            
    except Exception as e:
        error_msg = f"General error: {str(e)}"
        logger.error(f"\nError: {error_msg}")
        logger.error(traceback.format_exc())
        response = jsonify({
            'error': error_msg
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/summarize', methods=['POST'])
def summarize():
    try:
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        summary = summarize_large_text(text)
        return jsonify({
            'summary': summary,
            'original_length': len(text.split()),
            'summary_length': len(summary.split())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)