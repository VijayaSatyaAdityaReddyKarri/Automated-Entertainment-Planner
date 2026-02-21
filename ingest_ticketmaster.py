import psycopg2
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

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
    # Example format: 2026-02-19T14:00:00Z
    now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # --- Added &startDateTime= to the URL ---
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={TM_API_KEY}&city=Chicago&size=10&sort=date,asc&startDateTime={now_iso}"
    
    response = requests.get(url)
    
    # Check if the API call was successful
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
            # --- THE "TRANSFORM" STEP ---
            # APIs are messy. We use .get() to safely extract nested data without crashing.
            title = event.get('name', 'Unknown Event')
            
            # Extract Venue and City (Neighborhood) safely
            venues = event.get('_embedded', {}).get('venues', [{}])
            venue_name = venues[0].get('name', 'Unknown Venue')
            city_name = venues[0].get('city', {}).get('name', 'Chicago')
            
            # --- NEW CODE: Extract Latitude and Longitude safely ---
            try:
                lat = float(venues[0].get('location', {}).get('latitude'))
                lon = float(venues[0].get('location', {}).get('longitude'))
            except (KeyError, IndexError, TypeError, ValueError):
                # If Ticketmaster forgets to include coordinates, default to None (NULL in SQL)
                lat = None
                lon = None

            # Extract minimum price (if available)
            prices = event.get('priceRanges', [{}])
            price_min = prices[0].get('min', 0.0)
            
            # Extract category (Music, Sports, etc.)
            classifications = event.get('classifications', [{}])
            category = classifications[0].get('segment', {}).get('name', 'Live Event')
            
            # Use the Ticketmaster URL as the description for now
            event_url = event.get('url', 'No link available')

            # Extract the date and time
            event_date = event.get('dates', {}).get('start', {}).get('dateTime')
            if not event_date: # Fallback if they only provide a day, not a time
                event_date = event.get('dates', {}).get('start', {}).get('localDate')
            if not event_date: # Ultimate fallback: use the current timestamp
                event_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # --- THE "LOAD" STEP ---
            # Notice we added lat and lon to the columns list and %s values!
            cur.execute("""
                INSERT INTO raw_events (title, venue, neighborhood, price_min, category, is_discounted, deal_description, event_date, lat, lon)
                VALUES (%s, %s, %s, %s, %s, FALSE, %s, %s, %s, %s)
            """, (title, venue_name, city_name, price_min, category, event_url, event_date, lat, lon))
            
            inserted_count += 1

        conn.commit()
        print(f"✅ Success! Loaded {inserted_count} live events with coordinates into the database.")
        cur.close()

    except Exception as e:
        print(f"❌ Database Error: {e}")
    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    # Run the ETL Pipeline
    live_events = fetch_ticketmaster_events()
    if live_events:
        load_events_to_db(live_events)