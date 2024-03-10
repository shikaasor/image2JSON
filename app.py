from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st
import os
import json
import psycopg2
import re


load_dotenv()

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
    pattern = r"{[\s\S]*?(?=})"  # Matches anything between { and } (not greedy)
    match = re.search(pattern, response)
    if match:
        return match.group(0)
    else:
        return None

def insert_into_database(json_data):
    try:
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password='lamis',
            port='5432',
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Create the database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS data")

        # Connect to the 'data' database
        conn.close()
        conn = psycopg2.connect(
            host="localhost",
            database="data",
            user="postgres",
            password='lamis',
            port='5432',
        )
        cursor = conn.cursor()

        # Create the table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS json_data (
            id SERIAL PRIMARY KEY,
            data JSONB
        )
        """
        cursor.execute(create_table_query)

        # Insert the JSON data into the table
        insert_query = "INSERT INTO json_data (data) VALUES (%s)"
        cursor.execute(insert_query, (json_data,))

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

    st.header("Transcribe Handfilled Form Image To e-Form")
    uploaded_file = st.file_uploader("Choose image file to detect text",type=['jpeg','jpg','png'])
    image=""
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image.", use_column_width=True)
    
    submit = st.button("Extract Text")

    input_prompt=""""Read the handwritten text in the image and output what you see 
        in JSON format according to fields and values.
        Focus on fields that have evidence of handwriting and adhere strictly to what is written in the image.
    """

    if submit:
        image_data = load_image(uploaded_file)
        response = generate_text(image_data,input_prompt)
        st.subheader("Here is the requested data:")
        st.write(response)
        json_data = extract_json(response)
        
        # Extract JSON and save to database
        save = st.button("Save Data")
        if save:
            if json_data:
                insert_into_database(json_data)
                st.success("Extracted data saved to database!")
            else:
                st.warning("No valid JSON found in the response.")


if __name__ == "__main__":
    main()