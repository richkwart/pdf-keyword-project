# 🧾 PDF Keyword Project

## 📘 Overview
The **PDF Keyword Project** is a Python-based tool designed to automatically scan multiple PDF documents, extract text, and identify specific keywords or expertise tags.  
It helps users quickly summarize and organize information from a large collection of project charters, reports, or research papers.

---

## 🚀 Features
- 🔍 **Batch PDF Processing** – Scans all PDFs in a folder automatically.  
- 🧠 **Keyword Detection** – Identifies defined keywords or phrases (e.g., expertise areas, technologies, etc.).  
- 📊 **CSV Reporting** – Generates two detailed reports:
  - `keyword_hits.csv` – All detected keyword occurrences with file and page details.
  - `charter_summary.csv` – Summary of keywords found per PDF.
- ⚡ **Progress Tracking** – Uses a progress bar for real-time feedback.
- 🧩 **Extensible** – Easy to modify or add new keyword sets and detection logic.

---

## 🧰 Technologies Used
- **Python 3.x**
- **Libraries:**
  - `PyMuPDF (fitz)` – For PDF text extraction
  - `tqdm` – For progress visualization
  - `pandas` – For CSV report generation
  - `os`, `re` – For file handling and regex search

---

## 📂 Project Structure
pdf_keyword_project/
│
├── pdf_keyword_project.py # Main script
├── pdfs/ # Folder containing your PDFs
├── venv/ # Virtual environment (optional)
├── keyword_hits.csv # Generated results (auto-created)
├── charter_summary.csv # Summary results (auto-created)
├── requirements.txt # Dependencies list
└── README.md # Project documentation


---

## ⚙️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/richkwart/pdf-keyword-project.git
cd pdf-keyword-project

2. Create and Activate a Virtual Environment
python -m venv venv
venv\Scripts\activate

3. Install Dependencies
pip install -r requirements.txt


(If you don’t have a requirements.txt file, you can generate one with:)

pip freeze > requirements.txt

4. Add Your PDF Files

Place all PDFs you want to analyze into the /pdfs folder.

5. Run the Script
python pdf_keyword_project.py


After completion, two CSV files will be generated inside the pdfs folder:

keyword_hits.csv

charter_summary.csv

🧠 Future Enhancements

Add GUI or web dashboard to visualize results.

Include AI/NLP for smarter keyword detection and summarization.

Export reports to Excel or PDF formats.

Support for multiple keyword categories (e.g., skills, technologies, locations).

👨‍💻 Author

Richard Kwarteng
📍 Graduate Student, MS in Computer Management and Information Systems (SIUE)
💼 Passionate about AI, Data Analysis, and Cloud Computing.

🪪 License

This project is open-source and available under the MIT License


🧩 Example Requirements File (requirements.txt)
PyMuPDF
pandas
tqdm


⭐ If you find this project helpful, consider giving it a star on GitHub!

