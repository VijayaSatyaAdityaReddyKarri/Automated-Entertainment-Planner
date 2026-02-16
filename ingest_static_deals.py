import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

# Load the secrets from the .env file
load_dotenv()

# Safely pull the database credentials
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = "5432"
DB_NAME = "postgres"

def seed_recurring_deals():
    deals = [
        ('AMC Discount Tuesdays', 'AMC River East 21', 'Streeterville', 7.00, 'Movie', 'Member discount price'),
        ('Regal Value Tuesdays', 'Regal Webster Place', 'Lincoln Park', 7.99, 'Movie', 'Standard 2D movies'),
        ('Music Box Matinee', 'Music Box Theatre', 'Lakeview', 11.00, 'Movie', 'Before 5 PM daily'),
        ('Logan Theatre Open Mic', 'The Logan Theatre', 'Logan Square', 0.00, 'Comedy', 'Free entry, No cover'),
        ('Second City Student Standby', 'Second City', 'Old Town', 0.00, 'Comedy', 'Free tickets for students 1hr before show')
    ]

    conn = None 
    try:
        print("Connecting to the ETL Engine via IPv4 Session Pooler...")
        
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        cur = conn.cursor()

        print("Inserting deals...")
        for deal in deals:
            cur.execute("""
                INSERT INTO raw_events (title, venue, neighborhood, price_min, category, is_discounted, deal_description)
                VALUES (%s, %s, %s, %s, %s, TRUE, %s)
            """, deal)

        conn.commit()
        print(f"✅ Success! Ingested {len(deals)} deals.")
        cur.close()

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    seed_recurring_deals()