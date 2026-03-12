import streamlit as st
import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv
import folium
import folium.plugins as plugins
from streamlit_folium import st_folium

# Load database credentials
load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = "5432"
DB_NAME = "postgres"

# Page configuration - Set to wide mode and dark theme
st.set_page_config(page_title="Chicago Entertainment Planner", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM CSS FOR LOVABLE DESIGN ---
st.markdown("""
<style>
    /* Main Background & Text */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Custom Event Card */
    .event-card {
        background-color: #1A1C23;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #2D303E;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .event-card:hover {
        transform: translateY(-5px);
        border-color: #3B82F6;
    }
    
    /* Top Row: Category & Deal Badge */
    .card-header-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    .category-pill {
        background-color: rgba(59, 130, 246, 0.2);
        color: #60A5FA;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .deal-pill {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34D399;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    
    /* Title */
    .event-title {
        font-size: 18px;
        font-weight: bold;
        color: #FFFFFF;
        margin-bottom: 10px;
        line-height: 1.3;
    }
    
    /* Details (Time, Venue) */
    .event-detail {
        font-size: 13px;
        color: #A0AEC0;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
    }
    
    /* Bottom Row: Price & Button */
    .card-footer-row {
        margin-top: auto;
        padding-top: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px solid #2D303E;
    }
    .event-price {
        font-size: 20px;
        font-weight: bold;
        color: #FFFFFF;
    }
    .get-tickets-btn {
        background-color: #3B82F6;
        color: white !important;
        text-decoration: none;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: bold;
        text-align: center;
    }
    .get-tickets-btn:hover {
        background-color: #2563EB;
    }
    
    /* Deal Description Text */
    .deal-text {
        font-size: 12px;
        color: #60A5FA;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- DATA SERVING FUNCTION ---
@st.cache_data(ttl=3600)
def fetch_data():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
        )
        query = """
            SELECT title, event_date, venue, neighborhood, price_min, category, deal_description, is_discounted, lat, lon 
            FROM raw_events 
            WHERE event_date >= CURRENT_DATE
            ORDER BY event_date ASC, price_min ASC;
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        if 'event_date' in df.columns:
            df['event_date'] = pd.to_datetime(df['event_date'])
            
        return df
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return pd.DataFrame()

df = fetch_data()

# --- HEADER & FILTERS ---
st.title("🎭 Chicago Entertainment Planner")

if not df.empty:
    # Top Control Bar
    col1, col2, col3 = st.columns([2, 2, 6])
    
    with col1:
        categories = ["All"] + list(df['category'].unique())
        selected_category = st.selectbox("Filter by Category", categories, label_visibility="collapsed")
        
    with col2:
        st.write("") # Spacer
        show_only_free = st.toggle("Free Events Only")
        
    with col3:
        st.write("") # Spacer
        
    # Apply filters
    filtered_df = df.copy()
    if selected_category != "All":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if show_only_free:
        filtered_df = filtered_df[filtered_df['price_min'] == 0.0]

    st.markdown(f"<div style='text-align: right; color: #A0AEC0; margin-bottom: 20px;'>Showing <b>{len(filtered_df)}</b> Events</div>", unsafe_allow_html=True)

    # --- TABS LAYOUT ---
    tab1, tab2 = st.tabs(["📇 Event Feed", "📍 Live Map"])

    # --- TAB 1: EVENT FEED (LOVABLE CARDS) ---
    with tab1:
        # Create rows of 3 columns
        cols = st.columns(3)
        
        for index, row in filtered_df.iterrows():
            # Figure out which column this card goes into (0, 1, or 2)
            col_idx = index % 3
            
            # Format Data
            date_str = row['event_date'].strftime('%b %d, %Y - %I:%M %p') if pd.notnull(row['event_date']) else 'Time TBA'
            
            if pd.isna(row['price_min']):
                price_str = "Varies" 
            elif row['price_min'] > 0:
                price_str = f"${row['price_min']:.2f}"
            else:
                price_str = "FREE"
                
            deal_desc = str(row['deal_description']) if pd.notnull(row['deal_description']) else ""
            is_link = deal_desc.startswith('http')
            
            btn_text = "Get Tickets" if is_link and "ticket" in deal_desc.lower() else "More Info"
            btn_link = deal_desc if is_link else "#"
            deal_note = f"💡 {deal_desc}" if not is_link and deal_desc else ""

            # HTML Card Injection
            card_html = f"""
            <div class="event-card">
                <div class="card-header-row">
                    <span class="category-pill">{row['category']}</span>
                    {'<span class="deal-pill">Deal</span>' if deal_desc else ''}
                </div>
                
                <div class="event-title">{row['title']}</div>
                
                <div class="event-detail">📅 {date_str}</div>
                <div class="event-detail">📍 {row['venue']}</div>
                
                <div class="card-footer-row">
                    <div class="event-price">{price_str}</div>
                    <a href="{btn_link}" target="_blank" class="get-tickets-btn">{btn_text}</a>
                </div>
                
                <div class="deal-text">{deal_note}</div>
            </div>
            """
            
            # Render card in the correct column
            with cols[col_idx]:
                st.markdown(card_html, unsafe_allow_html=True)

    # --- TAB 2: LIVE MAP ---
    with tab2:
        map_df = filtered_df.dropna(subset=['lat', 'lon'])

        if not map_df.empty:
            chicago_map = folium.Map(location=[41.8781, -87.6298], zoom_start=11, tiles="CartoDB dark_matter")
            grouped = map_df.groupby(['venue', 'lat', 'lon'])

            for (venue, lat, lon), group in grouped:
                event_count = len(group)
                
                popup_html = f"""<div style="width: 250px; font-family: Arial; color: #333;">
                    <h4 style="margin-top: 0; color: #3B82F6;">{venue}</h4>
                    <p><b>{event_count} Event(s)</b></p>
                </div>"""

                icon = plugins.BeautifyIcon(
                    icon_shape='marker',
                    number=event_count,
                    border_color='#3B82F6',
                    text_color='#3B82F6',
                    background_color='#1A1C23'
                )

                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{venue}",
                    icon=icon
                ).add_to(chicago_map)

            st_folium(chicago_map, width="100%", height=600, returned_objects=[])
        else:
            st.info("No spatial data available for the current filters.")

else:
    st.warning("No data found. Is the ETL pipeline running?")