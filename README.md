Image2Form
Image2Form is a Streamlit-based application that extracts structured JSON data from handwritten forms using the Groq LLaMA Vision model. The extracted data is stored in a SQLite database and can be exported as an Excel report. This tool is ideal for automating data extraction from handwritten documents, such as patient forms, invoices, or surveys.

Features
Image Upload: Upload handwritten form images (JPEG, JPG, PNG).

AI-Powered Extraction: Extract structured JSON data using the Groq LLaMA Vision model.

Database Storage: Save extracted data to a SQLite database.

Excel Export: Generate and download an Excel report of all extracted data.

User-Friendly UI: Intuitive interface with visual feedback and progress indicators.

Data Management: Delete all records from the database via the sidebar.

Prerequisites
Before running the application, ensure you have the following installed:

Python 3.8+

Streamlit

Pillow (for image processing)

Groq Python SDK

Pandas (for Excel report generation)

SQLite3 (for database storage)

Installation
Clone the Repository:

git clone https://github.com/your-username/Image2Form.git
cd Image2Form

Set Up a Virtual Environment (optional but recommended):

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install Dependencies:

pip install -r requirements.txt
Set Up Environment Variables:

Create a .env file in the root directory.

Add your Groq API Key to the .env file:

GROQ_API_KEY=your_groq_api_key_here

Usage
Run the Application: streamlit run app.py

Upload an Image:

Use the file uploader to upload a handwritten form image (JPEG, JPG, or PNG).

Enter Document Name:

Provide a name for the document (e.g., "Patient Form", "Invoice").

Extract Data:

Click the Extract Text button to process the image and extract JSON data.

View and Save Data:

The extracted JSON data will be displayed on the screen.

The data is automatically saved to the SQLite database.

Generate Excel Report:

Click the Generate Excel Report button to download an Excel file containing all extracted data.

Delete Records:

Use the sidebar to delete all records from the database.

File Structure

Image2Form/
├── app.py                  # Main application script
├── requirements.txt        # List of dependencies
├── .env                    # Environment variables (e.g., API keys)
├── extracted_data.db       # SQLite database for storing extracted data
├── README.md               # Project documentation
└── extracted_data_report.xlsx  # Temporary Excel report (generated on demand)

Configuration
Environment Variables
GROQ_API_KEY: Your Groq API key for accessing the LLaMA Vision model.

Database
The application uses a SQLite database (extracted_data.db) to store extracted JSON data.

The database schema includes the following table:

sql

CREATE TABLE json_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_name TEXT,
    json_data TEXT,
    date_created DATETIME DEFAULT CURRENT_TIMESTAMP
);

Contributing
Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

Fork the repository.

Create a new branch for your feature or bugfix.

Commit your changes and push to the branch.

Submit a pull request.