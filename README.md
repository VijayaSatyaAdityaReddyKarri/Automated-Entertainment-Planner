# 🎟️ Chicago Automated Entertainment ETL Pipeline

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791.svg)](https://supabase.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Live_Dashboard-FF4B4B.svg)](https://entertainment-planner.streamlit.app/)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF.svg)](https://github.com/features/actions)

**[🔴 View the Live Dashboard Here](https://entertainment-planner.streamlit.app/)**

## 📖 Project Overview
This project is an end-to-end automated Data Engineering pipeline designed to extract, transform, and serve live entertainment and event data for the city of Chicago. It aggregates data from multiple disparate sources (REST APIs and static lists) into a centralized cloud data warehouse, making it accessible via an interactive web dashboard.

## 🏗️ Data Architecture
1. **Extract**: Python scripts extract real-time JSON data from the **Ticketmaster API** (live events) and the **Art Institute of Chicago API** (museum exhibitions).
2. **Transform**: The data is parsed, cleaned, and standardized. Missing fields are handled safely, and schema evolution was applied to attach ISO 8601 formatted execution timestamps (`event_date`).
3. **Load**: The cleaned data is loaded into a cloud-hosted **PostgreSQL** database (via Supabase) using the `psycopg2` adapter.
4. **Automate**: A **GitHub Actions** CI/CD workflow is triggered daily via cron job to spin up an Ubuntu runner, connect to the database securely using GitHub Secrets, and run the ingestion scripts to keep the data fresh.
5. **Serve**: A frontend data application built with **Streamlit** connects to the PostgreSQL database, retrieves the latest data via optimized SQL queries, and serves it to users with dynamic filtering capabilities.

## 🛠️ Technology Stack
* **Language:** Python 3.10
* **Data Sources:** Ticketmaster Discovery API, Art Institute of Chicago Public API
* **Cloud Database:** PostgreSQL (Supabase)
* **Automation / CI/CD:** GitHub Actions
* **Frontend / UI:** Streamlit Cloud
* **Libraries:** `pandas`, `psycopg2-binary`, `requests`, `python-dotenv`

## 🚀 Local Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/VijayaSatyaAdityaReddyKarri/Automated-Entertainment-Planner/tree/main](https://github.com/VijayaSatyaAdityaReddyKarri/Automated-Entertainment-Planner/tree/main)
   cd Automated-Entertainment-Planner