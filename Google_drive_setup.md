# 📂 Google Drive API Setup Guide
(Required for Intranet Agent)

This guide explains how to:
- Enable Google Drive API
- Create service account credentials
- Share your Drive folders
- Set `GOOGLE_DRIVE_CREDENTIALS_PATH`

---

## 🔹 Step 1: Create a Google Cloud Project

1. Go to 👉 [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Click **Select Project** → **New Project**
3. Name it (e.g., `Intranet-Policy-Agent`)
4. Click **Create**

---

## 🔹 Step 2: Enable Google Drive API

Inside your project:
1. Navigate to **APIs & Services** → **Library**
2. Search for: **Google Drive API**
3. Click **Enable**

---

## 🔹 Step 3: Create a Service Account

1. Go to: **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **Service Account**
3. Enter:
   - **Name**: `intranet-agent-sa`
4. Click **Create & Continue**
5. Skip roles (not required for Drive readonly access)
6. Click **Done**

---

## 🔹 Step 4: Generate Service Account Key

1. In **Credentials** page, click your **Service Account**
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON**
5. Click **Create**
6. A JSON file will download. **This is your credential file.**

**Keep this file secure. Do not commit it to Git.**

---

## 🔹 Step 5: Share Google Drive Folder

Service accounts do NOT automatically have access to your Drive.

1. Open the downloaded JSON file
2. Copy the value of: "client_email": "xxxxx@xxxxx.iam.gserviceaccount.com"
3. Go to your **Google Drive**
4. Right-click your LOB folder (Aero / Marine / Construction)
5. Click **Share**
6. Paste the `client_email`
7. Set permission to: **Viewer**
8. Click **Send**
9. Repeat for each LOB folder.

---

## 🔹 Step 6: Get Folder IDs

1. Open your folder in browser
2. URL looks like: https://drive.google.com/drive/folders/14567t6ADHDH73r3
3. The ID is: `14567t6ADHDH73r3`

Add these to your environment:

GOOGLE_DRIVE_AERO_FOLDER_ID=xxxxxxxx
GOOGLE_DRIVE_MARINE_FOLDER_ID=xxxxxxxx
GOOGLE_DRIVE_CONSTRUCTION_FOLDER_ID=xxxxxxxx 
GOOGLE_DRIVE_CASUALTY_FOLDER_ID=xxxxxxxx
GOOGLE_DRIVE_PROPERTY_FOLDER_ID=xxxxxxxx
GOOGLE_DRIVE_MOTOR_FOLDER_ID=xxxxxxxx
GOOGLE_DRIVE_ENERGY_FOLDER_ID=xxxxxxxx
GOOGLE_DRIVE_FINANCIAL_LINES_FOLDER_ID=xxxxxxxx

---

## 🔹 Step 7:Set GOOGLE_DRIVE_CREDENTIALS_PATH
Move the downloaded JSON file somewhere safe.

Example:/Users/yourname/secure/drive_credentials.json

Use a .env file:
GOOGLE_DRIVE_CREDENTIALS_PATH=/Users/yourname/secure/drive_credentials.json
