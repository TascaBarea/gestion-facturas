@echo off
cd /d C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas
call .\.venv\Scripts\activate
cd streamlit_app
streamlit run app.py