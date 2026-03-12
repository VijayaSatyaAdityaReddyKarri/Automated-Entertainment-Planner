import psycopg2
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

# This loads the secrets from your .env file
load_dotenv() 

# Now we pull them in safely!
TM_API_KEY = os.getenv("TM_API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = "5432"
DB_NAME = "postgres"

def fetch_ticketmaster_events():
    print("Extracting live data from Ticketmaster API...")
    
    # --- Get current time in ISO 8601 format for Ticketmaster ---
    now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={TM_API_KEY}&city=Chicago&size=10&sort=date,asc&startDateTime={now_iso}"
    
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code}")
        return []
        
    data = response.json()
    events = data.get('_embedded', {}).get('events', [])
    print(f"✅ Extracted {len(events)} events!")
    return events

def load_events_to_db(events):
    conn = None
    try:
        print("Connecting to the ETL Engine...")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        print("Transforming and Loading events...")
        inserted_count = 0
        
        for event in events:
            # --- PARSING THE EVENT DATA ---
            title = event.get('name', 'Unknown Event')
            
            # --- EXTRACT VENUE & LOCATION ---
            venues = event.get('_embedded', {}).get('venues', [{}])
            venue_name = venues[0].get('name', 'Unknown Venue')
            city_name = venues[0].get('city', {}).get('name', 'Chicago')
            
            try:
                lat = float(venues[0].get('location', {}).get('latitude'))
                lon = float(venues[0].get('location', {}).get('longitude'))
            except (KeyError, IndexError, TypeError, ValueError):
                lat = None
                lon = None

            # --- MISSING VARS FIX: CATEGORY & URL ---
            classifications = event.get('classifications', [])
            category = "Other"
            if classifications:
                category = classifications[0].get('segment', {}).get('name', 'Other')
                
            event_url = event.get('url', 'No link available')

            # --- THE PRICE FIX ---
            # Safely check if priceRanges actually exists and has data
            price_ranges = event.get('priceRanges')
            price_min = None  # <-- Changed from 0.0 to None
            if price_ranges and isinstance(price_ranges, list) and len(price_ranges) > 0:
                price_min = price_ranges[0].get('min', None) 

            # --- THE TIMEZONE FIX ---
            # Explicitly grab the venue's local date and time instead of UTC
            dates = event.get('dates', {}).get('start', {})
            local_date = dates.get('localDate')
            local_time = dates.get('localTime', '00:00:00') # Defaults to midnight if no time is given
            
            if local_date:
                event_date = f"{local_date} {local_time}"
            else:
                # Ultimate fallback
                event_date = dates.get('dateTime', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

            # --- DATABASE INSERTION ---
            cur.execute("""
                INSERT INTO raw_events (title, venue, neighborhood, price_min, category, is_discounted, deal_description, event_date, lat, lon)
                VALUES (%s, %s, %s, %s, %s, FALSE, %s, %s, %s, %s)
            """, (title, venue_name, city_name, price_min, category, event_url, event_date, lat, lon))
            
            inserted_count += 1

        conn.commit()
        print(f"✅ Success! Loaded {inserted_count} polished events.")
        cur.close()

    except Exception as e:
        print(f"❌ Database Error: {e}")
    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    live_events = fetch_ticketmaster_events()
    if live_events:
        load_events_to_db(live_events)