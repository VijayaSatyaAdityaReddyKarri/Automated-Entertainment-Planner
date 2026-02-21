import psycopg2
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

# Load the secrets from the .env file
load_dotenv()

# Safely pull the database credentials
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = "5432"
DB_NAME = "postgres"

def fetch_museum_exhibitions():
    print("Extracting live data from the Art Institute of Chicago API...")
    
    # We are calling the public API to get 5 currently running exhibitions
    url = "https://api.artic.edu/api/v1/exhibitions?limit=5&status=Running"
    
    # We use a custom User-Agent header, which is a good Data Engineering practice 
    # to let the server know who is politely scraping their data.
    headers = {'User-Agent': 'AEP ETL Engine (Student Project)'}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code}")
        return []
        
    data = response.json()
    exhibitions = data.get('data', [])
    print(f"✅ Extracted {len(exhibitions)} museum exhibitions!")
    return exhibitions

def load_exhibitions_to_db(exhibitions):
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
        
        print("Transforming and Loading museum data...")
        inserted_count = 0
        
        for exhibit in exhibitions:
            # --- TRANSFORM ---
            title = exhibit.get('title', 'Unknown Exhibition')
            venue = "Art Institute of Chicago"
            neighborhood = "The Loop"
            
            # The Art Institute is $26 for general admission, but free for IL residents on Thursdays.
            # We will log the standard price, but add the discount rule in the description.
            price_min = 26.00 
            category = "Museum/Art"
            description = "Free for Illinois residents on Thursdays 5 PM - 8 PM"
            
            # --- NEW CODE: Generate the timestamp ---
            event_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # --- LOAD ---
            # Notice we added event_date to the columns list, an extra %s, and event_date to the tuple!
            cur.execute("""
                INSERT INTO raw_events (title, venue, neighborhood, price_min, category, is_discounted, deal_description, event_date)
                VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s)
            """, (title, venue, neighborhood, price_min, category, description, event_date))
            
            inserted_count += 1

        conn.commit()
        print(f"✅ Success! Loaded {inserted_count} exhibitions into the database.")
        cur.close()

    except Exception as e:
        print(f"❌ Database Error: {e}")
    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    exhibits = fetch_museum_exhibitions()
    if exhibits:
        load_exhibitions_to_db(exhibits)