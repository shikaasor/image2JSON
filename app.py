from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st
import os
import json
import psycopg2
import re

#load environment variables
load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = os.getenv('DB_PORT')
genai.configure(api_key=os.getenv('API_KEY'))


def load_image(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        image_parts = [
            {
                "mime_type": uploaded_file.type,
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")

def generate_text(image,prompt):
    model = genai.GenerativeModel("gemini-pro-vision")
    response = model.generate_content(
        [image[0],prompt],
        generation_config={
            "max_output_tokens": 2048,
            "temperature": 0.4,
            "top_p": 1,
            "top_k": 32
        },
    )
    return response.text

def save_text_to_file(response, predefined_folder):
    if not os.path.exists(predefined_folder):
        os.makedirs(predefined_folder)
    file_path = os.path.join(predefined_folder, 'imageText' + '.json')
    with open(file_path, 'w') as file:
        file.write(response)


def extract_json(response):
    pattern = r"\{[\s\S]+\}"
    try:
        match = re.search(pattern, response)
        if match:
            json_data = match.group()
            return json_data
        else:
            return None
    except Exception as e:
        print(f"Error extracting JSON data: {e}")
        return None

def insert_into_database(json_data):
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Create the database if it doesn't exist
        cursor.execute("SELECT datname FROM pg_catalog.pg_database WHERE datname=%s", ('data',))
        db_exists = cursor.fetchone()
        if not db_exists:
            cursor.execute("CREATE DATABASE data")

        # Connect to the 'data' database
        conn.close()
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
        )
        cursor = conn.cursor()

        # Create the table if it doesn't exist
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'json_data')")
        table_exists = cursor.fetchone()[0]
        if not table_exists:
            create_table_query = """
            CREATE TABLE json_data (
                id SERIAL PRIMARY KEY,
                data JSONB
            )
            """
            cursor.execute(create_table_query)
        
        # validate json data
        parsed_json = json.loads(json_data)
        sanitized_json = json.dumps(parsed_json)

        # Insert the JSON data into the table
        insert_query = "INSERT INTO json_data (data) VALUES (%s)"
        cursor.execute(insert_query, (sanitized_json,))

        conn.commit()
        st.success("JSON data inserted into the database.")
    except (Exception, psycopg2.Error) as error:
        st.error(f"Error inserting JSON data into the database: {error}")
    finally:
        if conn:
            cursor.close()
            conn.close()


def main():
    
    st.set_page_config(page_title="Image2Form")

    st.header("Extract Data From Handfilled Form Image To JSON")
    uploaded_file = st.file_uploader("Choose image file to detect text",type=['jpeg','jpg','png'])
    image=""
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image.", use_column_width=True)
    
    submit = st.button("Extract Text")

    input_prompt=""""Analyze the handwritten text in the image and create a structured JSON output representing the extracted data. 
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

    if submit:
        image_data = load_image(uploaded_file)
        response = generate_text(image_data,input_prompt)
        st.subheader("Here is the requested data:")
        st.write(response)
        save_text_to_file(response, "./extractedText")
        json_data = extract_json(response)
        st.write(json_data)
        # Extract JSON and save to database
        # save = st.button("Save Data")
        # if save:
        if json_data:
            insert_into_database(json_data)
            st.success("Extracted data saved to database!")
        else:
            st.warning("No valid JSON found in the response.")


if __name__ == "__main__":
    main()