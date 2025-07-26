# 📊 BOM Consumption Tracker

This Streamlit web app helps production teams track BOM (Bill of Materials) usage across multiple TV models, based on a planned production schedule. Upload the required input files and get a consolidated report showing required quantities, available stock, and shortages per part number.

---

## 🚀 Features

- Upload production plan and BOM files
- Calculates total required quantity per part
- Checks against available stock
- Highlights shortages and excess
- Exports final report as a downloadable Excel

---

## 🛠️ Tech Stack

- **Python**
- **Streamlit**
- **Pandas**
- **OpenPyXL / XlsxWriter**

---

## 📂 How to Run Locally

1. **Clone the repository**

```bash
git clone https://github.com/kshitiz510/material-shortage-generator.git
cd material-shortage-generator
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Run the app**

```bash
streamlit run app.py
```
