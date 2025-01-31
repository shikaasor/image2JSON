from PIL import Image
from dotenv import load_dotenv
import groq
import streamlit as st
import pandas as pd
import os
import json
import psycopg2
import re
import base64
import logging
from psycopg2 import pool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Validate environment variables
required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_PORT', 'GROQ_API_KEY']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")

DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = os.getenv('DB_PORT')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Initialize Groq client
groq_client = groq.Client(api_key=GROQ_API_KEY)

# Database connection pool
db_pool = pool.SimpleConnectionPool(
    1, 10,  # min, max connections
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    port=DB_PORT
)

def load_image(uploaded_file):
    """Load and prepare image for processing"""
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        return [{
            "mime_type": uploaded_file.type,
            "data": bytes_data
        }]
    else:
        raise FileNotFoundError("No file uploaded")

def generate_text(image, prompt):
    """Generate text from image using Groq LLaMA Vision model"""
    try:
        # Encode image data as base64
        base64_image = base64.b64encode(image[0]["data"]).decode("utf-8")
        
        # Prepare the request for Groq API
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image[0]['mime_type']};base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model="llama-3.2-11b-vision-preview",  # Use the correct Groq model
            temperature=0.4,
            top_p=1,
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating text: {e}")
        st.error("Failed to generate text from the image. Please try again.")
        raise

def save_text_to_file(response, predefined_folder):
    """Save extracted text to a file"""
    if not os.path.exists(predefined_folder):
        os.makedirs(predefined_folder)
    file_path = os.path.join(predefined_folder, 'imageText.json')
    with open(file_path, 'w') as file:
        file.write(response)

def extract_json(response):
    """Extract JSON data from the response"""
    pattern = r"\{[\s\S]+\}"
    try:
        match = re.search(pattern, response)
        if match:
            json_data = match.group()
            return json_data
        else:
            return None
    except Exception as e:
        logger.error(f"Error extracting JSON data: {e}")
        st.error("Failed to extract JSON data from the response.")
        return None

def ensure_database_exists():
    """Ensure the target database exists"""
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            database="postgres"
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("SELECT datname FROM pg_catalog.pg_database WHERE datname=%s", (DB_NAME,))
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            logger.info(f"Database '{DB_NAME}' created.")
    except Exception as e:
        logger.error(f"Error ensuring database exists: {e}")
        raise
    finally:
        if conn:
            conn.close()

def ensure_table_exists():
    """Ensure the required table exists"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS json_data (
                id SERIAL PRIMARY KEY,
                document_name TEXT,
                json_data JSONB,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Error ensuring table exists: {e}")
        raise
    finally:
        db_pool.putconn(conn)

def insert_into_database(document_name, json_data):
    """Insert JSON data into the database"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        insert_query = "INSERT INTO json_data (document_name, json_data) VALUES (%s, %s)"
        cursor.execute(insert_query, (document_name, json_data))
        conn.commit()
        st.success("JSON data inserted into the database.")
    except Exception as e:
        logger.error(f"Error inserting JSON data: {e}")
        st.error("Failed to insert JSON data into the database.")
        if conn:
            conn.rollback()
    finally:
        db_pool.putconn(conn)

def generate_excel_report():
    """Generate Excel report from database contents"""
    conn = db_pool.getconn()
    try:
        df = pd.read_sql_query("SELECT * FROM json_data", conn)
        excel_path = 'extracted_data_report.xlsx'
        df.to_excel(excel_path, index=False)
        
        st.success("Excel report generated successfully.")
        with open(excel_path, 'rb') as f:
            st.download_button(
                label="Download Excel Report",
                data=f,
                file_name='extracted_data_report.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        # Clean up the temporary file
        os.remove(excel_path)
    except Exception as e:
        logger.error(f"Error generating Excel report: {e}")
        st.error("Failed to generate Excel report.")
    finally:
        db_pool.putconn(conn)

def main():
    """Main Streamlit application"""
    st.set_page_config(page_title="Image2JSON", layout="wide")
    st.header("Extract Data From Handfilled Form Image")

    # Document name input
    document_name = st.text_input("Enter Document Name", placeholder="e.g., Patient Form, Invoice")

    # Image upload section
    uploaded_file = st.file_uploader("Choose image file to detect text", type=['jpeg', 'jpg', 'png'])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image.", use_column_width=True)
    
    # Extract text button
    submit = st.button("Extract Text")

    # Prompt for text generation
    input_prompt = """Analyze the handwritten text in the image and create a structured JSON output representing the extracted data. 
    * Identify all fields with clear handwriting evidence within the image.
    * Exclude any information not explicitly written in the image.
    * Represent each field as a key-value pair in the JSON structure.
    * Use descriptive and consistent field names based on the extracted information.
    * Ensure the generated JSON is well-formed and valid.
    
    Here's an example format for the JSON output:
    {
        "field1": "value1",
        "field2": "value2",
        "field3": "value3"
    }
    """

    # Text extraction process
    if submit and uploaded_file and document_name:
        try:
            image_data = load_image(uploaded_file)
            response = generate_text(image_data, input_prompt)
            st.subheader("Extracted Data:")
            st.write(response)
            
            json_data = extract_json(response)
            if json_data:
                st.json(json_data)
                insert_into_database(document_name, json_data)
            else:
                st.warning("No valid JSON found in the response.")
        except Exception as e:
            logger.error(f"Error during text extraction: {e}")
            st.error("An error occurred during text extraction. Please try again.")

    # Excel report generation
    if st.button("Generate Excel Report"):
        generate_excel_report()

if __name__ == "__main__":
    ensure_database_exists()
    ensure_table_exists()
    main()