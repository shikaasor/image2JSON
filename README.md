Image2Form

This Streamlit application leverages the power of Gemini-Pro Vision to extract data from handwritten form images and convert it into a structured JSON format.

What it Does:

    Uploads an image file (JPEG, JPG, or PNG) containing a handwritten form.
    Uses Gemini-Pro Vision to analyze the image and extract textual information.
    Generates a JSON output representing the extracted data as key-value pairs.
    Optionally stores the extracted JSON data in a PostgreSQL database (requires configuration).

How to Use:

Clone the Repository:

Bash
git clone https://github.com/shikaasor/image2JSON.git

Set Up Environment:

Install required libraries (pip install -r requirements.txt).
Create a .env file in the project root and set environment variables for database connection (refer to the code for details).
Obtain a Google Cloud Platform project and API key for Gemini-Pro Vision access (instructions on https://cloud.google.com/).

Run the App:

streamlit run app.py

Upload an Image:

Click "Choose image file to detect text" and select the image file containing the handwritten form.
Click "Extract Text" to process the image.

Output:

The application displays the uploaded image.
It displays the extracted text from the image.
A well-formatted JSON representation of the extracted data is shown (if successful).
Optionally, a success message confirms saving the extracted data to the database (requires configuration).
Additional Notes:

The application utilizes a pre-defined prompt to guide Gemini-Pro Vision in extracting relevant data from the form.
The database functionality is currently commented out (# Save Data button). To enable it, uncomment the relevant section and configure your database connection details.
Feel free to explore and customize the application further!