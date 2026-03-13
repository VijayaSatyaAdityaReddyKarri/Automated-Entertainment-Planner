import streamlit as st
import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv
import folium
import folium.plugins as plugins
from streamlit_folium import st_folium
import urllib.parse
from datetime import datetime

# Load database credentials
load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = "5432"
DB_NAME = "postgres"

# Page configuration
st.set_page_config(page_title="Chicago Entertainment Planner", layout="wide", initial_sidebar_state="collapsed")

# Dynamic Category Color Mapping (consistent everywhere)
CATEGORY_COLORS = {
    "Museum/Art": ("#B026FF", "rgba(176, 38, 255, 0.15)"),   
    "Comedy": ("#FFB300", "rgba(255, 179, 0, 0.15)"),        
    "Theater": ("#FF3366", "rgba(255, 51, 102, 0.15)"),      
    "Music": ("#3B82F6", "rgba(59, 130, 246, 0.15)"),        
    "Food & Drink": ("#00E676", "rgba(0, 230, 118, 0.15)"),  
    "Sports": ("#F97316", "rgba(249, 115, 22, 0.15)"),       
    "Movie": ("#06B6D4", "rgba(6, 182, 212, 0.15)"),
    "undefined": ("#94A3B8", "rgba(148, 163, 184, 0.15)") # Special case from DB
}

# --- PURE CYBERPUNK CSS & BACKGROUND ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --foreground: #F8FAFC;
        --card: rgba(15, 23, 42, 0.4); 
        --primary: #00D2FF; 
        --primary-alpha: rgba(0, 210, 255, 0.1);
        --success: #00E676; 
        --success-alpha: rgba(0, 230, 118, 0.1);
        --muted-foreground: #94A3B8;
        --border: rgba(30, 41, 59, 0.8);
        --surface: rgba(15, 23, 42, 0.8);
    }

    /* Full-screen Blurred Background Image */
    #background-container {
        position: fixed;
        width: 100vw;
        height: 100vh;
        background-image: url('https://images.unsplash.com/photo-1549474843-ed8344e43e2f?q=80&w=2070&auto=format&fit=crop&blur=8&brightness=0.3');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        z-index: -1;
        opacity: 0.6; /* Dim it further for better readability */
        backdrop-filter: blur(15px); /* Ensure base blur if image load fails */
    }

    /* Glassmorphism content container */
    [data-testid="stAppViewContainer"] {
        color: var(--foreground);
        font-family: 'Inter', sans-serif;
        background-color: transparent;
    }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Adjust Streamlit block containers */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
        background-color: transparent !important;
    }

    /* 2. Streamlit Tabs */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background-color: var(--surface);
        padding: 4px;
        border-radius: 0.75rem;
        gap: 4px;
        border: 1px solid var(--border);
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
        background-color: var(--primary-alpha);
        color: var(--primary);
        border: 1px solid var(--primary);
        box-shadow: 0 0 15px rgba(0, 210, 255, 0.2); 
    }
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] p {
        color: var(--primary) !important;
    }

    /* 3. Live Badge Pulse */
    @keyframes ripple-wave {
        0% { box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.8); }
        100% { box-shadow: 0 0 0 12px rgba(0, 230, 118, 0); }
    }
    
    @keyframes radar-glow {
        0%, 100% { 
            filter: brightness(1) drop-shadow(0 0 0px rgba(0, 230, 118, 0)); 
        }
        50% { 
            filter: brightness(1.4) drop-shadow(0 0 5px rgba(0, 230, 118, 0.8)); 
        }
    }

    .live-badge {
        display: inline-flex;
        align-items: center;
        background-color: var(--surface);
        padding: 6px 12px;
        border-radius: 20px;
        border: 1px solid var(--border);
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 15px;
        gap: 6px;
        backdrop-filter: blur(10px);
    }
    .pulse-dot {
        width: 8px; 
        height: 8px;
        background-color: var(--success);
        border-radius: 50%;
        animation: ripple-wave 1.5s infinite cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    .radar-icon {
        animation: radar-glow 2s infinite ease-in-out;
    }
    .live-count {
        color: var(--success);
        font-weight: 700;
    }
    .live-text {
        color: var(--muted-foreground);
    }

    /* 4. Glassmorphism Event Card */
    @keyframes fade-in {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .event-card {
        background-color: var(--card);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 0.75rem; 
        padding: 1.25rem; 
        margin-bottom: 24px; 
        cursor: pointer;
        animation: fade-in 0.3s ease-out forwards;
        transition: all 0.3s ease; 
        border: 1px solid var(--border);
        height: 310px; 
        display: flex;
        flex-direction: column;
        font-family: 'Inter', sans-serif;
    }
    .event-card:hover {
        transform: translateY(-4px);
        border-color: var(--primary);
        box-shadow: 0 0 20px rgba(0, 210, 255, 0.15), inset 0 0 10px rgba(0, 210, 255, 0.05); 
    }

    /* Card Elements */
    .card-top-row { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1rem; }
    
    .pill-category { 
        font-size: 0.75rem; font-weight: 600; padding: 0.25rem 0.625rem; border-radius: 9999px; 
        border: 1px solid transparent;
    }
    .pill-deal { 
        font-size: 0.75rem; font-weight: 600; padding: 0.25rem 0.625rem; border-radius: 9999px; 
        background-color: var(--success-alpha); color: var(--success); border: 1px solid rgba(0, 230, 118, 0.3);
        box-shadow: 0 0 8px rgba(0, 230, 118, 0.2);
    }
    
    .card-title { 
        font-weight: 700; color: var(--foreground); font-size: 1.1rem; 
        margin-bottom: 0.75rem; line-height: 1.375; transition: color 0.2s; 
        margin-top: 0; 
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; 
        min-height: 48px; 
    }
    .event-card:hover .card-title { color: var(--primary); }

    .card-meta { display: flex; align-items: center; gap: 0.5rem; color: var(--muted-foreground); font-size: 0.85rem; margin-bottom: 0.5rem; }
    
    /* Footer & Neon Buttons */
    .card-footer { display: flex; align-items: center; justify-content: space-between; padding-top: 1rem; margin-top: auto; border-top: 1px solid rgba(255,255,255,0.05); }
    .price-text { font-size: 1.25rem; font-weight: 800; color: var(--foreground); }
    .price-free { font-size: 1.25rem; font-weight: 800; color: var(--success); text-shadow: 0 0 10px rgba(0, 230, 118, 0.4); }
    
    .btn-primary { 
        display: inline-flex; align-items: center; padding: 0.5rem 1rem; font-size: 0.8rem; font-weight: 700; 
        border-radius: 2rem; background-color: var(--primary); color: #0B0F19 !important; text-decoration: none;
        box-shadow: 0 0 12px rgba(0, 210, 255, 0.4); transition: all 0.2s; border: 1px solid var(--primary);
    }
    .btn-primary:hover { 
        box-shadow: 0 0 20px rgba(0, 210, 255, 0.6); transform: scale(1.02); background-color: #33DBFF;
    }
    
    .btn-secondary {
        display: inline-flex; align-items: center; padding: 0.5rem 1rem; font-size: 0.8rem; font-weight: 700; 
        border-radius: 2rem; background-color: var(--primary-alpha); color: var(--primary) !important; text-decoration: none;
        border: 1px solid var(--primary); transition: all 0.2s; box-shadow: 0 0 8px rgba(0, 210, 255, 0.1);
    }
    .btn-secondary:hover { 
        background-color: rgba(0, 210, 255, 0.2); box-shadow: 0 0 15px rgba(0, 210, 255, 0.3); transform: scale(1.02);
    }
    
    .deal-text { margin-top: 0.75rem; font-size: 0.75rem; color: var(--success); font-weight: 500; margin-bottom: 0; 
                 display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }

    /* 5. Custom Horizontal Pill Filter Bar */
    .filter-pills-row {
        background-color: var(--surface);
        backdrop-filter: blur(10px);
        padding: 10px;
        border-radius: 0.75rem;
        border: 1px solid var(--border);
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 20px;
    }
    .filter-label {
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--foreground);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 5px;
    }
    .filter-pills-container {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap; /* allow wrapping on smaller screens */
    }
    
    /* Updated Pill CSS */
    .filter-pill {
        display: inline-block;
        border-radius: 9999px;
        padding: 8px 16px;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
    }
    .filter-pill:hover {
        transform: translateY(-2px);
    }

</style>

<div id="background-container"></div>
""", unsafe_allow_html=True)

# Function to generate the pill filter bar HTML
def get_filter_pills_html(categories, current_selection):
    pills_html = ""
    
    def make_pill(cat_name, cat_color, cat_bg, is_active):
        # Use ? instead of # so Streamlit reads it as a query parameter
        safe_cat = urllib.parse.quote_plus(cat_name)
        href_link = f"?category={safe_cat}"
        
        if is_active:
            # Active state: Full neon glow and colored background
            style = f"background-color: {cat_bg}; color: {cat_color}; border: 1px solid {cat_color}; box-shadow: 0 0 12px {cat_bg};"
            return f'<a href="{href_link}" target="_self" class="filter-pill" style="{style}">{cat_name}</a>'
        else:
            # Inactive state: Dark glass button, grey text. Lights up on hover via inline JS!
            style = f"background-color: rgba(15, 23, 42, 0.6); color: #94A3B8; border: 1px solid rgba(255,255,255,0.1);"
            hover_in = f"this.style.borderColor='{cat_color}'; this.style.color='{cat_color}'; this.style.backgroundColor='{cat_bg}'; this.style.boxShadow='0 0 8px {cat_bg}';"
            hover_out = f"this.style.borderColor='rgba(255,255,255,0.1)'; this.style.color='#94A3B8'; this.style.backgroundColor='rgba(15, 23, 42, 0.6)'; this.style.boxShadow='none';"
            return f'<a href="{href_link}" target="_self" class="filter-pill" style="{style}" onmouseover="{hover_in}" onmouseout="{hover_out}">{cat_name}</a>'

    # Add "All" Pill
    all_is_active = current_selection == "All"
    pills_html += make_pill("All", "#F8FAFC", "rgba(248, 250, 252, 0.15)", all_is_active)

    # Add dynamic category pills
    for cat in categories:
        is_active = current_selection == cat
        cat_color, cat_bg = CATEGORY_COLORS.get(cat, ("#94A3B8", "rgba(148, 163, 184, 0.15)")) 
        pills_html += make_pill(cat, cat_color, cat_bg, is_active)
    
    return pills_html

@st.cache_data(ttl=3600)
def fetch_data():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
        )
        # Use CURRENT_DATE to get events happening *today* or in the future
        query = f"""
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

# Handle pill selection via query params
selected_cat = "All"
if "category" in st.query_params:
    selected_cat = urllib.parse.unquote_plus(st.query_params["category"])

if not df.empty:
    colA, colB = st.columns([3, 1])
    with colA:
        st.markdown("<h2 style='color: white; margin-bottom: 0; font-family: Inter;'>⚡ Chicago Entertainment Planner</h2>", unsafe_allow_html=True)
    with colB:
        st.markdown(f"""
        <div style="text-align: right; margin-top: 10px;">
            <div class="live-badge">
                <div class="pulse-dot"></div>
                <svg class="radar-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00E676" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4.9 19.1c-3.9-3.9-3.9-10.3 0-14.2"></path>
                    <path d="M8.4 15.6c-2-2-2-5.2 0-7.2"></path>
                    <circle cx="12" cy="12" r="2" fill="#00E676" stroke="none"></circle>
                    <path d="M15.6 8.4c2 2 2 5.2 0 7.2"></path>
                    <path d="M19.1 4.9c3.9 3.9 3.9 10.3 0 14.2"></path>
                </svg>
                <span class="live-count">{len(df)}</span>
                <span class="live-text">Live Events</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- NEW UNIFIED HORIZONTAL FILTER ROW ---
    st.write("") 
    filter_container = st.container()
    with filter_container:
        # Create columns for the horizontal pills and the existing free-only toggle
        f_pill_col, f_toggle_col = st.columns([10, 2])
        
        with f_pill_col:
            # Generate the HTML for the pills
            all_categories = list(df['category'].dropna().unique())
            st.markdown(f"""
            <div class="filter-pills-row">
                <div class="filter-label">Filter by:</div>
                <div class="filter-pills-container">
                    {get_filter_pills_html(all_categories, selected_cat)}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with f_toggle_col:
            # Shift it slightly to align with the new pills row
            st.write("") 
            st.write("")
            show_only_free = st.toggle("Free Events Only")

    # Apply all filters
    filtered_df = df.copy()
    if selected_cat != "All":
        filtered_df = filtered_df[filtered_df['category'] == selected_cat]
    if show_only_free:
        filtered_df = filtered_df[filtered_df['price_min'] == 0.0]

    st.write("") 
    tab1, tab2 = st.tabs(["📇 Event Feed", "📍 Live Map"])

    with tab1:
        cols = st.columns(3)
        for index, row in filtered_df.reset_index().iterrows():
            col_idx = index % 3
            
            # Format date for the card
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
                btn_text = "Get Tickets ↗" if "ticket" in deal_desc.lower() else "More Info ↗"
                btn_class = "btn-primary"
                link_url = deal_desc
            else:
                btn_text = "Search Event ↗"
                btn_class = "btn-secondary" 
                # Create a specific search query for the user
                search_query = urllib.parse.quote_plus(f"{row['title']} {row['venue']} Chicago")
                link_url = f"https://www.google.com/search?q={search_query}"
                
            btn_html = f'<a href="{link_url}" target="_blank" class="{btn_class}">{btn_text}</a>'
                
            deal_note = f"✨ {deal_desc}" if not is_link and deal_desc else ""
            deal_badge = '<span class="pill-deal">Deal</span>' if deal_desc or row.get('is_discounted') else ''
            price_class = "price-free" if price_str == "FREE" else "price-text"

            # Dynamic Category Color Logic
            cat_val = row['category']
            cat_color, cat_bg = CATEGORY_COLORS.get(cat_val, ("#94A3B8", "rgba(148, 163, 184, 0.15)")) 

            card_html = f"""
            <div class="event-card" style="animation-delay: {index * 30}ms;">
                <div class="card-top-row">
                    <span class="pill-category" style="color: {cat_color}; background-color: {cat_bg}; border-color: {cat_color}40;">
                        {cat_val}
                    </span>
                    {deal_badge}
                </div>
                <h3 class="card-title" title="{row['title']}">{row['title']}</h3>
                <div style="margin-bottom: 1rem;">
                    <div class="card-meta">📅 <span>{date_str}</span></div>
                    <div class="card-meta">📍 <span>{row['venue']}</span></div>
                </div>
                <div class="card-footer">
                    <div style="display: flex; align-items: center; gap: 0.375rem;">
                        <span style="color: var(--muted-foreground); font-size: 14px;">🏷️</span>
                        <span class="{price_class}">{price_str}</span>
                    </div>
                    {btn_html}
                </div>
                {f'<p class="deal-text" title="{deal_note}">{deal_note}</p>' if deal_note else ''}
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
                
                # Compiling multiple events per venue into a structured list
                events_list_html = ""
                for _, e_row in group.iterrows():
                    e_title = str(e_row['title']).replace("'", "&#39;")
                    e_time = e_row['event_date'].strftime('%I:%M %p') if pd.notnull(e_row['event_date']) else ''
                    e_price = "FREE" if e_row['price_min'] == 0 else (f"${e_row['price_min']:.2f}" if pd.notnull(e_row['price_min']) else "Varies")
                    
                    events_list_html += f"""
                    <li style='margin-bottom: 6px; line-height: 1.2;'>
                        <strong style="color: #00D2FF;">{e_title}</strong><br>
                        <span style='color: #94A3B8; font-size: 11px;'>{e_time} • {e_price}</span>
                    </li>
                    """

                popup_html = f"""
                <div style="width: 260px; font-family: 'Inter', sans-serif; background: #0B0F19; padding: 10px; border-radius: 8px;">
                    <h4 style="margin-top: 0; color: #F8FAFC; margin-bottom: 10px; padding-bottom: 5px; border-bottom: 1px solid #1E293B; font-size: 14px;">{venue}</h4>
                    <ul style="padding-left: 15px; margin-top: 0; font-size: 12px; list-style-type: none; margin: 0; padding: 0;">
                        {events_list_html}
                    </ul>
                </div>
                """

                # Matching BeautifyIcon color to the primary neon
                icon = plugins.BeautifyIcon(
                    icon_shape='marker',
                    number=event_count,
                    border_color='#00D2FF',
                    text_color='#00D2FF',
                    background_color='#0B0F19'
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