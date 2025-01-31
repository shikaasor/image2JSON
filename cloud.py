import os
import re
import json
import base64
import sqlite3
import streamlit as st
import pandas as pd
from PIL import Image
from dotenv import load_dotenv
import groq
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
DATABASE_PATH = 'extracted_data.db'

# Initialize Groq client
groq_client = groq.Client(api_key=GROQ_API_KEY)

def initialize_database():
    """Create SQLite database and table with specified schema"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS json_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT,
            json_data TEXT,
            date_created DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def load_image(uploaded_file):
    """Load and prepare image for processing"""
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        return [{
            "mime_type": uploaded_file.type,
            "data": bytes_data
        }]
    raise FileNotFoundError("No file uploaded")

def generate_text(image, prompt):
    """Generate text from image using Groq LLaMA Vision model"""
    try:
        base64_image = base64.b64encode(image[0]["data"]).decode("utf-8")
        
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
            model="llama-3.2-11b-vision-preview",
            temperature=0.4,
            top_p=1,
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating text: {e}")
        st.error("Failed to generate text from the image. Please try again.")
        raise

def extract_json(response):
    """Extract JSON data from the response"""
    pattern = r"\{[\s\S]+\}"
    try:
        match = re.search(pattern, response)
        return match.group() if match else None
    except Exception as e:
        logger.error(f"Error extracting JSON data: {e}")
        st.error("Failed to extract JSON data from the response.")
        return None

def insert_json_to_database(document_name, json_data):
    """Insert JSON data into SQLite database with document name"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        # Validate JSON
        json.loads(json_data)
        
        cursor.execute(
            "INSERT INTO json_data (document_name, json_data) VALUES (?, ?)", 
            (document_name, json_data)
        )
        conn.commit()
        st.success("JSON data inserted into the database.")
    except json.JSONDecodeError:
        st.error("Invalid JSON data")
    except sqlite3.Error as e:
        logger.error(f"Database insertion error: {e}")
        st.error("Failed to insert JSON data into the database.")
    finally:
        conn.close()

def generate_excel_report():
    """Generate Excel report from database contents"""
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # Read data from SQLite to DataFrame
        df = pd.read_sql_query("SELECT * FROM json_data", conn)
        
        # Save to Excel
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
        conn.close()

def delete_records():
    """Delete all records from the database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM json_data")
        conn.commit()
        st.success("All records deleted from the database.")
    except sqlite3.Error as e:
        logger.error(f"Error deleting records: {e}")
        st.error("Failed to delete records from the database.")
    finally:
        conn.close()

def cleanup_temp_files():
    """Clean up temporary files"""
    if os.path.exists('extracted_data_report.xlsx'):
        os.remove('extracted_data_report.xlsx')

def main():
    """Main Streamlit application"""
    initialize_database()
    
    # Set page config
    st.set_page_config(
        page_title="Image2Form",
        page_icon="📄",
        layout="wide"
    )

    # Sidebar for navigation and additional options
    with st.sidebar:
        st.title("Navigation")
        st.markdown("""
            - **Upload an image** to extract data.
            - **Generate an Excel report** from the database.
            - **Delete all records** from the database.
        """)
        if st.button("Delete All Records"):
            delete_records()

    # Main content
    st.title("📄 Image2Form")
    st.markdown("Extract structured JSON data from handwritten forms using AI.")

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
        with st.spinner("Extracting data from the image..."):
            try:
                image_data = load_image(uploaded_file)
                response = generate_text(image_data, input_prompt)
                st.subheader("Extracted Data:")
                st.write(response)
                
                json_data = extract_json(response)
                if json_data:
                    st.json(json_data)
                    insert_json_to_database(document_name, json_data)
                else:
                    st.warning("No valid JSON found in the response.")
            except Exception as e:
                logger.error(f"Error during text extraction: {e}")
                st.error("An error occurred during text extraction. Please try again.")

    # Excel report generation
    if st.button("Generate Excel Report"):
        with st.spinner("Generating Excel report..."):
            generate_excel_report()

    # Clean up temporary files
    cleanup_temp_files()

if __name__ == "__main__":
    main()