import os
import re
import json
import tempfile
import uuid
import base64
from datetime import datetime
import streamlit as st
import pandas as pd
from PIL import Image
from dotenv import load_dotenv
import groq
import logging
from supabase import create_client, Client



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
DATABASE_PATH = 'extracted_data.db'

# Initialize Groq client
groq_client = groq.Client(api_key=GROQ_API_KEY)

# setup supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

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
            model="llama-3.2-90b-vision-preview",
            temperature=1,
            stream=False,
            top_p=1,
            response_format={"type":"json_object"},
            stop=None,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating text: {e}", exc_info=True)
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

def insert_json_to_database(id, document_name, json_data, time_now):
    """Insert JSON data into SQLite database with document name"""
    try:
        # Validate JSON
        json_data_final = json.loads(json_data)
        print(json_data_final)
        
        response = supabase.table("json_data").insert({"id": id, "document_name": document_name, "json_data": json_data_final, "date_created": time_now}).execute()

        st.success("JSON data inserted into the database.")
    except response.Error as e:
        logger.error(f"Database insertion error: {e}")
        st.error("Failed to insert JSON data into the database.")

def fetch_data_from_supabase():
    """Generate Excel report from database contents"""
    try:
        # Read data from supabase
        response = supabase.table("json_data").select("*").execute()
        if response.data:
            return response.data
        else:
            logger.warning("No data found in the database.")
            return []
    except Exception as e:
        logger.error(f"Error fetching data from Supabase: {e}")
        st.error("Failed to fetch data from the database")

def generate_excel_report():
    try:
        data = fetch_data_from_supabase()
        if not data:
            st.warning("No data available to generate report.")
            return
        
        df = pd.DataFrame(data)

        # Save to Excel
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            excel_path = tmp_file.name
            df.to_excel(excel_path, index=False)
            
            st.success("Excel report generated successfully.")
            with open(excel_path, 'rb') as f:
                st.download_button(
                    label="Download Excel Report",
                    data=f,
                    file_name='extracted_data_report.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
        
        # Clean up the temporary file after download
        os.unlink(excel_path)
    except Exception as e:
        logger.error(f"Error generating Excel report: {e}")
        st.error("Failed to generate Excel report.")

def cleanup_temp_files():
    """Clean up temporary files"""
    if os.path.exists('extracted_data_report.xlsx'):
        os.remove('extracted_data_report.xlsx')

def main():
    """Main Streamlit application"""
    
    # Set page config
    st.set_page_config(
        page_title="Image2JSON",
        page_icon="📄",
        layout="wide"
    )

    # Sidebar for navigation and additional options
    with st.sidebar:
        st.title("Navigation")
        st.markdown("""
            - **Upload an image** to extract data.
            - **Generate an Excel report** from the database.
        """)

    # Main content
    st.title("📄 Image2JSON")
    st.markdown("Extract structured JSON data from handwritten forms using AI.")

    # Document name input
    document_name = st.text_input("Enter Document Name", placeholder="e.g., Patient Form, Invoice", help="Provide a name for the document to help identify it later.")

    # Image upload section
    uploaded_file = st.file_uploader("Choose image file to detect text", type=['jpeg', 'jpg', 'png'], help="Upload an image containing handwritten or printed text.")
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image.")
    
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
    if 'json_data' not in st.session_state:
        st.session_state.json_data = None

    if submit and uploaded_file and document_name:
        with st.spinner("Extracting data from the image..."):
            try:
                image_data = load_image(uploaded_file)
                response = generate_text(image_data, input_prompt)
                st.session_state.json_data = response

                if st.session_state.json_data:
                    json_data = st.session_state.json_data
                    st.json(json_data)
                    id = str(uuid.uuid4())
                    time_now = datetime.now().isoformat()
                    insert_json_to_database(id, document_name, json_data, time_now)
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