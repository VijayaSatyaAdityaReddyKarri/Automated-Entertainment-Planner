import streamlit as st
import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

# Load database credentials
load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = "5432"
DB_NAME = "postgres"

# Page configuration
st.set_page_config(page_title="Automated Entertainment Planner", layout="wide")
st.title("🎟️ Chicago Automated Entertainment Planner")
st.markdown("This dashboard serves live data extracted from Ticketmaster, Museums, and static sources via an automated ETL pipeline.")

# --- DATA SERVING FUNCTION ---
# We use st.cache_data so we don't hit the database every single time the user clicks a button
@st.cache_data(ttl=3600) # Cache the data for 1 hour
def fetch_data():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        # The Data Engineer's query to serve the downstream app
        query = """
            SELECT title, venue, neighborhood, price_min, category, deal_description, is_discounted 
            FROM raw_events 
            ORDER BY price_min ASC;
        """
        # Load the SQL results directly into a Pandas DataFrame
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return pd.DataFrame()

# Fetch the data
df = fetch_data()

# --- THE USER INTERFACE ---
if not df.empty:
    # Create some interactive filters for the user
    st.subheader("Filter Events")
    col1, col2 = st.columns(2)
    
    with col1:
        categories = ["All"] + list(df['category'].unique())
        selected_category = st.selectbox("Select Category", categories)
        
    with col2:
        show_only_free = st.checkbox("Show Only Free Events ($0.00)")

    # Apply the filters to the Pandas DataFrame
    filtered_df = df.copy()
    if selected_category != "All":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if show_only_free:
        filtered_df = filtered_df[filtered_df['price_min'] == 0.0]

    # Display the final data
    st.dataframe(
        filtered_df, 
        use_container_width=True,
        hide_index=True,
        column_config={
            "price_min": st.column_config.NumberColumn("Minimum Price ($)", format="$%.2f")
        }
    )
    
    # Show a quick DE metric
    st.metric(label="Total Events in Database", value=len(filtered_df))

else:
    st.warning("No data found. Is the ETL pipeline running?")