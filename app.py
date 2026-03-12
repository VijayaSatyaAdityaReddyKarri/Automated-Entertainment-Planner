import streamlit as st
import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv
import folium
import folium.plugins as plugins
from streamlit_folium import st_folium
import urllib.parse

# Load database credentials
load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = "5432"
DB_NAME = "postgres"

# Page configuration
st.set_page_config(page_title="Chicago Entertainment Planner", layout="wide", initial_sidebar_state="collapsed")

# --- THE LOVABLE HEIST: PIXEL-PERFECT CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --background: hsl(0, 0%, 7%);
        --foreground: hsl(0, 0%, 96%);
        --card: hsl(0, 0%, 11%);
        --primary: hsl(217, 91%, 60%);
        --primary-alpha: hsla(217, 91%, 60%, 0.1);
        --success: hsl(152, 69%, 53%);
        --success-alpha: hsla(152, 69%, 53%, 0.1);
        --muted-foreground: hsl(0, 0%, 64%);
        --border: hsl(0, 0%, 20%);
        --surface: hsl(240, 6%, 12%);
    }

    /* 1. Global App Styling */
    [data-testid="stAppViewContainer"] {
        background-color: var(--background);
        color: var(--foreground);
        font-family: 'Inter', sans-serif;
    }
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* 2. Hijacking Streamlit Tabs to look like Lovable Buttons */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background-color: var(--surface);
        padding: 4px;
        border-radius: 0.75rem;
        gap: 4px;
        border: none;
        width: max-content;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        background-color: transparent;
        color: var(--muted-foreground);
        border-radius: 0.5rem;
        padding: 10px 20px;
        font-size: 0.875rem;
        font-weight: 600;
        border: none;
        transition: all 0.2s ease;
    }
    [data-testid="stTabs"] [data-baseweb="tab"]:hover {
        color: var(--foreground);
    }
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        background-color: var(--primary);
        color: white;
        box-shadow: 0 0 20px -5px hsla(217, 91%, 60%, 0.4); /* glow-primary */
    }
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] p {
        color: white !important;
    }

    /* 3. Live Badge Pulse */
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(34, 197, 94, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }
    .live-badge {
        display: inline-flex;
        align-items: center;
        background-color: var(--surface);
        padding: 6px 12px;
        border-radius: 20px;
        border: 1px solid var(--border);
        color: var(--muted-foreground);
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 15px;
        font-family: 'Inter', sans-serif;
    }
    .pulse-dot {
        width: 8px; height: 8px;
        background-color: var(--success);
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }

    /* 4. Event Card Base (from EventCard.tsx) */
    @keyframes fade-in {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .event-card {
        background-color: var(--card);
        border-radius: 0.5rem; 
        padding: 1.25rem; 
        cursor: pointer;
        animation: fade-in 0.3s ease-out forwards;
        transition: transform 0.2s ease, box-shadow 0.2s ease; 
        border: 1px solid var(--border);
        height: 100%;
        display: flex;
        flex-direction: column;
        font-family: 'Inter', sans-serif;
    }
    .event-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px -10px hsla(217, 91%, 60%, 0.25);
    }

    /* Card Elements */
    .card-top-row { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 0.75rem; }
    .pill-category { font-size: 0.75rem; font-weight: 500; padding: 0.25rem 0.625rem; border-radius: 9999px; background-color: var(--primary-alpha); color: var(--primary); }
    .pill-deal { font-size: 0.75rem; font-weight: 500; padding: 0.25rem 0.625rem; border-radius: 9999px; background-color: var(--success-alpha); color: var(--success); }
    
    .card-title { font-weight: 600; color: var(--foreground); font-size: 1rem; margin-bottom: 0.75rem; line-height: 1.375; transition: color 0.2s; margin-top: 0; }
    .event-card:hover .card-title { color: var(--primary); }

    .card-meta { display: flex; align-items: center; gap: 0.5rem; color: var(--muted-foreground); font-size: 0.875rem; margin-bottom: 0.5rem; }
    
    /* Footer & Buttons */
    .card-footer { display: flex; align-items: center; justify-content: space-between; padding-top: 0.75rem; margin-top: auto; border-top: 1px solid hsla(0,0%,20%,0.5); }
    .price-text { font-size: 1.125rem; font-weight: 700; color: var(--foreground); }
    .price-free { font-size: 1.125rem; font-weight: 700; color: var(--success); }
    
    .btn-primary { 
        display: inline-flex; align-items: center; padding: 0.5rem 1rem; font-size: 0.75rem; font-weight: 600; 
        border-radius: 0.5rem; background-color: var(--primary); color: white !important; text-decoration: none;
        box-shadow: 0 0 20px -5px hsla(217, 91%, 60%, 0.4); transition: background-color 0.2s;
    }
    .btn-primary:hover { background-color: hsla(217, 91%, 60%, 0.9); }
    
    /* Secondary ghost button for search */
    .btn-secondary {
        display: inline-flex; align-items: center; padding: 0.5rem 1rem; font-size: 0.75rem; font-weight: 600; 
        border-radius: 0.5rem; background-color: transparent; color: var(--primary) !important; text-decoration: none;
        border: 1px solid hsla(217, 91%, 60%, 0.5); transition: all 0.2s;
    }
    .btn-secondary:hover { background-color: var(--primary-alpha); border-color: var(--primary); }
    
    .deal-text { margin-top: 0.75rem; font-size: 0.75rem; color: hsla(217, 91%, 60%, 0.8); font-weight: 500; margin-bottom: 0; }
</style>
""", unsafe_allow_html=True)

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

if not df.empty:
    colA, colB = st.columns([3, 1])
    with colA:
        st.markdown("<h2 style='color: white; margin-bottom: 0; font-family: Inter;'>🎭 Chicago Entertainment Planner</h2>", unsafe_allow_html=True)
    with colB:
        st.markdown(f"""
        <div style="text-align: right; margin-top: 10px;">
            <div class="live-badge">
                <div class="pulse-dot"></div>
                {len(df)} Live Events
            </div>
        </div>
        """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 6])
    
    with col1:
        categories = ["All"] + list(df['category'].unique())
        selected_category = st.selectbox("Filter by Category", categories, label_visibility="collapsed")
        
    with col2:
        st.write("") 
        show_only_free = st.toggle("Free Events Only")
        
    filtered_df = df.copy()
    if selected_category != "All":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if show_only_free:
        filtered_df = filtered_df[filtered_df['price_min'] == 0.0]

    st.write("") 
    tab1, tab2 = st.tabs(["📇 Event Feed", "📍 Live Map"])

    with tab1:
        cols = st.columns(3)
        for index, row in filtered_df.reset_index().iterrows():
            col_idx = index % 3
            
            # --- YOUR ORIGINAL LOGIC KEEPS GOING HERE ---
            date_str = row['event_date'].strftime('%b %d, %Y - %I:%M %p') if pd.notnull(row['event_date']) else 'Time TBA'
            
            if pd.isna(row['price_min']):
                price_str = "Varies" 
            elif row['price_min'] > 0:
                price_str = f"${row['price_min']:.2f}"
            else:
                price_str = "FREE"
                
            deal_desc = str(row['deal_description']) if pd.notnull(row['deal_description']) else ""
            is_link = deal_desc.startswith('http')
            
            if is_link:
                btn_text = "Get Tickets" if "ticket" in deal_desc.lower() else "More Info"
                btn_class = "btn-primary"
                link_url = deal_desc
            else:
                btn_text = "Search Event"
                btn_class = "btn-secondary" # Using the Lovable Ghost style for secondary buttons
                search_query = urllib.parse.quote_plus(f"{row['title']} {row['venue']} Chicago")
                link_url = f"https://www.google.com/search?q={search_query}"
                
            btn_html = f'<a href="{link_url}" target="_blank" class="{btn_class}">{btn_text}</a>'
                
            deal_note = f"💡 {deal_desc}" if not is_link and deal_desc else ""
            deal_badge = '<span class="pill-deal">Deal</span>' if deal_desc or row.get('is_discounted') else ''
            price_class = "price-free" if price_str == "FREE" else "price-text"

            # --- LOVABLE HTML INJECTION ---
            card_html = f"""
            <div class="event-card" style="animation-delay: {index * 50}ms;">
                <div class="card-top-row">
                    <span class="pill-category">{row['category']}</span>
                    {deal_badge}
                </div>
                <h3 class="card-title">{row['title']}</h3>
                <div style="margin-bottom: 1rem;">
                    <div class="card-meta">📅 <span>{date_str}</span></div>
                    <div class="card-meta">📍 <span>{row['venue']}</span></div>
                </div>
                <div class="card-footer">
                    <div style="display: flex; align-items: center; gap: 0.375rem;">
                        <span style="color: hsl(0,0%,64%); font-size: 14px;">🏷️</span>
                        <span class="{price_class}">{price_str}</span>
                    </div>
                    {btn_html}
                </div>
                {f'<p class="deal-text">{deal_note}</p>' if deal_note else ''}
            </div>
            """
            
            with cols[col_idx]:
                st.markdown(card_html, unsafe_allow_html=True)

    with tab2:
        map_df = filtered_df.dropna(subset=['lat', 'lon'])

        if not map_df.empty:
            chicago_map = folium.Map(location=[41.8781, -87.6298], zoom_start=11, tiles="CartoDB dark_matter", scrollWheelZoom=False)
            grouped = map_df.groupby(['venue', 'lat', 'lon'])

            for (venue, lat, lon), group in grouped:
                event_count = len(group)
                
                # --- YOUR EXACT MAP POPUP AND BEAUTIFY ICON LOGIC ---
                events_list_html = ""
                for _, e_row in group.iterrows():
                    e_title = str(e_row['title']).replace("'", "&#39;")
                    e_time = e_row['event_date'].strftime('%I:%M %p') if pd.notnull(e_row['event_date']) else ''
                    e_price = "FREE" if e_row['price_min'] == 0 else (f"${e_row['price_min']:.2f}" if pd.notnull(e_row['price_min']) else "Varies")
                    
                    events_list_html += f"""
                    <li style='margin-bottom: 6px; line-height: 1.2;'>
                        <strong>{e_title}</strong><br>
                        <span style='color: #666; font-size: 11px;'>{e_time} • {e_price}</span>
                    </li>
                    """

                popup_html = f"""
                <div style="width: 260px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #333; max-height: 250px; overflow-y: auto;">
                    <h4 style="margin-top: 0; color: #3B82F6; margin-bottom: 10px; padding-bottom: 5px; border-bottom: 1px solid #E5E7EB; font-size: 14px;">{venue}</h4>
                    <ul style="padding-left: 15px; margin-top: 0; font-size: 12px; list-style-type: disc;">
                        {events_list_html}
                    </ul>
                </div>
                """

                icon = plugins.BeautifyIcon(
                    icon_shape='marker',
                    number=event_count,
                    border_color='#3B82F6',
                    text_color='#3B82F6',
                    background_color='#111827'
                )

                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{venue} ({event_count} Events)",
                    icon=icon
                ).add_to(chicago_map)

            st_folium(chicago_map, width="100%", height=600, returned_objects=[])
        else:
            st.info("No spatial data available for the current filters.")

else:
    st.warning("No data found. Is the ETL pipeline running?")