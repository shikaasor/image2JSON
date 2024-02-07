from PIL import Image
from dotenv import load_dotenv
load_dotenv()
from io import BytesIO
import google.generativeai as genai
import streamlit as st
import base64
import os


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
    file_path = os.path.join(predefined_folder, 'imageText' + '.txt')
    with open(file_path, 'w') as file:
        file.write(response)

def main():
    
    st.set_page_config(page_title="Image2Form")

    st.header("Transcribe Handfilled Form Image To e-Form")
    uploaded_file = st.file_uploader("Choose image file to detect text",type=['jpeg','jpg','png'])
    image=""
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image.", use_column_width=True)
    
    submit = st.button("Extract Text")

    input_prompt="""Read the text in the image and output what you see 
        in JSON format according to fields and values
    """

    if submit:
        image_data = load_image(uploaded_file)
        response = generate_text(image_data,input_prompt)
        st.subheader("The response is")
        st.write(response)
        save_text_to_file(response,"./extractedText")


if __name__ == "__main__":
    main()