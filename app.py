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

# Page configuration
st.set_page_config(page_title="Automated Entertainment Planner", layout="wide")
st.title("🎟️ Chicago Automated Entertainment Planner")
st.markdown("This dashboard serves live data extracted from Ticketmaster, Museums, and static sources via an automated ETL pipeline.")

# --- DATA SERVING FUNCTION ---
@st.cache_data(ttl=3600)
def fetch_data():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        query = """
            SELECT title, event_date, venue, neighborhood, price_min, category, deal_description, is_discounted, lat, lon 
            FROM raw_events 
            ORDER BY event_date ASC, price_min ASC;
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Tell Pandas to treat this column as a true Date/Time object
        if 'event_date' in df.columns:
            df['event_date'] = pd.to_datetime(df['event_date'])
            
        return df
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return pd.DataFrame()

# Fetch the data
df = fetch_data()

# --- THE USER INTERFACE ---
if not df.empty:
    st.subheader("Filter Events")
    col1, col2 = st.columns(2)
    
    with col1:
        categories = ["All"] + list(df['category'].unique())
        selected_category = st.selectbox("Select Category", categories)
        
    with col2:
        show_only_free = st.checkbox("Show Only Free Events ($0.00)")

    # Apply filters
    filtered_df = df.copy()
    if selected_category != "All":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if show_only_free:
        filtered_df = filtered_df[filtered_df['price_min'] == 0.0]

    # --- 1. THE DATA TABLE (Moved to Top) ---
    st.write("---")
    st.subheader("📋 Event Details")
    
    # Display the final data
    st.dataframe(
        filtered_df, 
        use_container_width=True,
        hide_index=True,
        column_config={
            "price_min": st.column_config.NumberColumn("Minimum Price ($)", format="$%.2f"),
            "event_date": st.column_config.DatetimeColumn("Date & Time", format="MMM DD, YYYY - hh:mm a"),
            "deal_description": st.column_config.LinkColumn("Deal / Link"), # Makes URLs clickable in the table too!
            "lat": None, # Hides the raw coordinate column from users
            "lon": None  # Hides the raw coordinate column from users
        }
    )
    
    st.metric(label="Total Events in Database", value=len(filtered_df))


    # --- 2. THE INTERACTIVE MAP (Moved to Bottom) ---
    st.write("---")
    st.subheader("🗺️ Live Event Map")

    # Filter out any rows that don't have coordinates
    map_df = filtered_df.dropna(subset=['lat', 'lon'])

    if not map_df.empty:
        # Create the Base Map centered on Chicago
        chicago_map = folium.Map(location=[41.8781, -87.6298], zoom_start=11, tiles="CartoDB dark_matter")

        # Group events by Venue
        grouped = map_df.groupby(['venue', 'lat', 'lon'])

        for (venue, lat, lon), group in grouped:
            event_count = len(group)
            
            # Build a rich HTML Pop-up
            popup_html = f"""
            <div style="width: 320px; max-height: 250px; overflow-y: auto; font-family: Arial, sans-serif; color: #333;">
                <h4 style="margin-top: 0; margin-bottom: 5px; color: #E50914;">{venue}</h4>
                <div style="font-size: 12px; margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 5px;">
                    <b>{event_count} Event(s) happening here</b>
                </div>
            """
            
            # Loop through every single event at this venue
            for _, row in group.iterrows():
                date_str = row['event_date'].strftime('%b %d, %Y - %I:%M %p') if pd.notnull(row['event_date']) else 'Time TBA'
                price_str = f"${row['price_min']:.2f}" if row['price_min'] > 0 else "Free"
                
                popup_html += f"""
                <div style="margin-bottom: 12px;">
                    <strong style="font-size: 14px;">{row['title']}</strong><br>
                    <span style="font-size: 12px;">📅 {date_str}</span><br>
                    <span style="font-size: 12px;">🎟️ {row['category']} | 💵 {price_str}</span><br>
                """
                
                # --- NEW: SMART LINK LOGIC ---
                if pd.notnull(row['deal_description']):
                    desc = str(row['deal_description'])
                    # Check if it's a URL
                    if desc.startswith('http'):
                        popup_html += f'<span style="font-size: 11px;">🔗 <a href="{desc}" target="_blank" style="color: #1E90FF; text-decoration: none;"><b>Website</b></a></span><br>'
                    else:
                        popup_html += f'<span style="font-size: 11px; color: #666;">💡 <i>{desc}</i></span><br>'
                
                popup_html += "</div>"
            
            popup_html += "</div>"

            # Create a dynamic numbered icon
            icon = plugins.BeautifyIcon(
                icon_shape='marker',
                number=event_count,
                border_color='#E50914',
                text_color='#E50914',
                background_color='white'
            )

            # Add the marker to the map
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"Click to see {event_count} event(s) at {venue}",
                icon=icon
            ).add_to(chicago_map)

        # Display the map in Streamlit
        st_folium(chicago_map, width=1200, height=500, returned_objects=[])
    else:
        st.info("No spatial data available for the current filters.")

else:
    st.warning("No data found. Is the ETL pipeline running?")