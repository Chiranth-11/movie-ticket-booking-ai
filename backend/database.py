import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .config import DB_FILE, SEAT_TIER_PRICING

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Movies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        genre TEXT NOT NULL,
        language TEXT NOT NULL,
        duration_mins INTEGER NOT NULL,
        rating REAL NOT NULL,
        poster_url TEXT NOT NULL,
        description TEXT NOT NULL,
        director TEXT NOT NULL,
        cast TEXT NOT NULL,
        release_year INTEGER NOT NULL,
        backdrop_url TEXT
    )
    """)

    # Showtimes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS showtimes (
        id TEXT PRIMARY KEY,
        movie_id TEXT NOT NULL,
        theater_name TEXT NOT NULL,
        screen_type TEXT NOT NULL,
        screen_number INTEGER NOT NULL,
        date TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        base_price REAL NOT NULL,
        FOREIGN KEY (movie_id) REFERENCES movies(id)
    )
    """)

    # Seats table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seats (
        showtime_id TEXT NOT NULL,
        seat_id TEXT NOT NULL,
        row TEXT NOT NULL,
        number INTEGER NOT NULL,
        tier TEXT NOT NULL,
        price REAL NOT NULL,
        status TEXT NOT NULL,
        held_by TEXT,
        held_until TEXT,
        PRIMARY KEY (showtime_id, seat_id),
        FOREIGN KEY (showtime_id) REFERENCES showtimes(id)
    )
    """)

    # Bookings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        booking_id TEXT PRIMARY KEY,
        showtime_id TEXT NOT NULL,
        movie_id TEXT NOT NULL,
        movie_title TEXT NOT NULL,
        theater_name TEXT NOT NULL,
        screen_type TEXT NOT NULL,
        date TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        seat_ids TEXT NOT NULL,
        subtotal REAL NOT NULL,
        discount REAL NOT NULL,
        taxes_and_fees REAL NOT NULL,
        total_amount REAL NOT NULL,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        status TEXT NOT NULL,
        booked_at TEXT NOT NULL,
        qr_code_data TEXT NOT NULL
    )
    """)

    conn.commit()

    # Seed or synchronize missing movies
    seed_data(conn)

def seed_data(conn):
    cursor = conn.cursor()

    movies_data = [
        # Western / Global Classics
        {
            "id": "mov-inception",
            "title": "Inception",
            "genre": json.dumps(["Sci-Fi", "Action", "Thriller"]),
            "language": "English",
            "duration_mins": 148,
            "rating": 8.8,
            "poster_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=600&q=80",
            "description": "A skilled thief is given a chance at erasing his criminal history if he can implant an idea into the subconscious mind of a CEO.",
            "director": "Christopher Nolan",
            "cast": json.dumps(["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page", "Tom Hardy"]),
            "release_year": 2010,
            "backdrop_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80"
        },
        {
            "id": "mov-interstellar",
            "title": "Interstellar",
            "genre": json.dumps(["Sci-Fi", "Adventure", "Drama"]),
            "language": "English",
            "duration_mins": 169,
            "rating": 8.7,
            "poster_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=600&q=80",
            "description": "When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot is tasked to pilot a spacecraft along with a team of researchers to find a new planet for humans.",
            "director": "Christopher Nolan",
            "cast": json.dumps(["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain", "Michael Caine"]),
            "release_year": 2014,
            "backdrop_url": "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?auto=format&fit=crop&w=1200&q=80"
        },
        {
            "id": "mov-oppenheimer",
            "title": "Oppenheimer",
            "genre": json.dumps(["Biography", "Drama", "History"]),
            "language": "English",
            "duration_mins": 180,
            "rating": 8.9,
            "poster_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=600&q=80",
            "description": "The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb during World War II.",
            "director": "Christopher Nolan",
            "cast": json.dumps(["Cillian Murphy", "Emily Blunt", "Matt Damon", "Robert Downey Jr."]),
            "release_year": 2023,
            "backdrop_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=1200&q=80"
        },
        {
            "id": "mov-dark-knight",
            "title": "The Dark Knight",
            "genre": json.dumps(["Action", "Crime", "Drama"]),
            "language": "English",
            "duration_mins": 152,
            "rating": 9.0,
            "poster_url": "https://images.unsplash.com/photo-1509281373149-e957c6296406?auto=format&fit=crop&w=600&q=80",
            "description": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
            "director": "Christopher Nolan",
            "cast": json.dumps(["Christian Bale", "Heath Ledger", "Aaron Eckhart", "Michael Caine"]),
            "release_year": 2008,
            "backdrop_url": "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?auto=format&fit=crop&w=1200&q=80"
        },
        {
            "id": "mov-spirited-away",
            "title": "Spirited Away",
            "genre": json.dumps(["Animation", "Fantasy", "Family"]),
            "language": "Japanese",
            "duration_mins": 125,
            "rating": 8.6,
            "poster_url": "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=600&q=80",
            "description": "During her family's move to the suburbs, a sullen 10-year-old girl wanders into a world ruled by gods, witches, and spirits, and where humans are changed into beasts.",
            "director": "Hayao Miyazaki",
            "cast": json.dumps(["Rumi Hiiragi", "Miyu Irino", "Mari Natsuki"]),
            "release_year": 2001,
            "backdrop_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80"
        },
        {
            "id": "mov-dune2",
            "title": "Dune: Part Two",
            "genre": json.dumps(["Sci-Fi", "Adventure", "Action"]),
            "language": "English",
            "duration_mins": 166,
            "rating": 8.8,
            "poster_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=600&q=80",
            "description": "Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.",
            "director": "Denis Villeneuve",
            "cast": json.dumps(["Timothée Chalamet", "Zendaya", "Rebecca Ferguson", "Javier Bardem"]),
            "release_year": 2024,
            "backdrop_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1200&q=80"
        },

        # Indian Cinema Masterpieces
        {
            "id": "mov-kantara",
            "title": "Kantara",
            "genre": json.dumps(["Action", "Drama", "Thriller", "Indian Cinema"]),
            "language": "Kannada",
            "duration_mins": 148,
            "rating": 8.3,
            "poster_url": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&w=600&q=80",
            "description": "Set in the mystical coastal forests of Karnataka, a rebellious youth must embrace his ancestral deity Bhoota Kola when greed and injustice threaten his sacred clan.",
            "director": "Rishab Shetty",
            "cast": json.dumps(["Rishab Shetty", "Sapthami Gowda", "Kishore Kumar G.", "Achyuth Kumar"]),
            "release_year": 2022,
            "backdrop_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80"
        },
        {
            "id": "mov-rrr",
            "title": "RRR",
            "genre": json.dumps(["Action", "Drama", "History", "Indian Cinema"]),
            "language": "Telugu",
            "duration_mins": 187,
            "rating": 8.8,
            "poster_url": "https://images.unsplash.com/photo-1533613220915-609f661a6fe1?auto=format&fit=crop&w=600&q=80",
            "description": "A fearless tribal warrior and an intrepid officer in the 1920s British Raj forge an unbreakable bond before fighting side by side in an awe-inspiring liberation epic.",
            "director": "S.S. Rajamouli",
            "cast": json.dumps(["N.T. Rama Rao Jr.", "Ram Charan", "Alia Bhatt", "Ajay Devgn"]),
            "release_year": 2022,
            "backdrop_url": "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?auto=format&fit=crop&w=1200&q=80"
        },
        {
            "id": "mov-kgf2",
            "title": "K.G.F: Chapter 2",
            "genre": json.dumps(["Action", "Crime", "Drama", "Indian Cinema"]),
            "language": "Kannada",
            "duration_mins": 168,
            "rating": 8.4,
            "poster_url": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?auto=format&fit=crop&w=600&q=80",
            "description": "In the blood-soaked Kolar Gold Fields, Rocky's name strikes fear into his foes while he wages war against ruthless rivals, crime syndicates, and the government to retain absolute supremacy.",
            "director": "Prashanth Neel",
            "cast": json.dumps(["Yash", "Sanjay Dutt", "Raveena Tandon", "Srinidhi Shetty"]),
            "release_year": 2022,
            "backdrop_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1200&q=80"
        },
        {
            "id": "mov-3-idiots",
            "title": "3 Idiots",
            "genre": json.dumps(["Comedy", "Drama", "Indian Cinema"]),
            "language": "Hindi",
            "duration_mins": 170,
            "rating": 8.4,
            "poster_url": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=600&q=80",
            "description": "Two friends embark on a hilarious cross-country journey to track down their free-thinking college buddy Rancho, whose unconventional wisdom transformed their lives forever.",
            "director": "Rajkumar Hirani",
            "cast": json.dumps(["Aamir Khan", "R. Madhavan", "Sharman Joshi", "Kareena Kapoor"]),
            "release_year": 2009,
            "backdrop_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80"
        },
        {
            "id": "mov-baahubali2",
            "title": "Baahubali 2: The Conclusion",
            "genre": json.dumps(["Action", "Fantasy", "Drama", "Indian Cinema"]),
            "language": "Telugu",
            "duration_mins": 167,
            "rating": 8.2,
            "poster_url": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=600&q=80",
            "description": "Amarendra Baahubali upholds justice amidst treacherous royal court conspiracies, while his son Mahendra returns to Mahishmati to avenge his father's demise and claim the throne.",
            "director": "S.S. Rajamouli",
            "cast": json.dumps(["Prabhas", "Rana Daggubati", "Anushka Shetty", "Tamannaah Bhatia"]),
            "release_year": 2017,
            "backdrop_url": "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?auto=format&fit=crop&w=1200&q=80"
        },
        {
            "id": "mov-dangal",
            "title": "Dangal",
            "genre": json.dumps(["Biography", "Drama", "Sport", "Indian Cinema"]),
            "language": "Hindi",
            "duration_mins": 161,
            "rating": 8.3,
            "poster_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=600&q=80",
            "description": "Former wrestler Mahavir Singh Phogat overcomes orthodox prejudice by training his daughters Geeta and Babita to triumph at the Commonwealth Games, inspiring a nation.",
            "director": "Nitesh Tiwari",
            "cast": json.dumps(["Aamir Khan", "Fatima Sana Shaikh", "Sanya Malhotra", "Sakshi Tanwar"]),
            "release_year": 2016,
            "backdrop_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=1200&q=80"
        }
    ]

    cursor.execute("SELECT id FROM movies")
    existing_ids = set(r["id"] for r in cursor.fetchall())

    theaters = [
        {"name": "Cineplex Grand IMAX", "screen": "IMAX 3D Laser", "base": 20.0},
        {"name": "Starlight Dolby Cinema", "screen": "Dolby Atmos 4K", "base": 18.0},
        {"name": "Galaxy Premiere Hall", "screen": "Standard Digital", "base": 14.0}
    ]

    today = datetime.now()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)]
    time_slots = ["11:00 AM", "02:30 PM", "06:15 PM", "09:30 PM"]

    cursor.execute("SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER)) as max_id FROM showtimes")
    max_sh = cursor.fetchone()["max_id"] or 100
    sh_counter = max_sh + 1

    new_showtimes = []
    rows = ["A", "B", "C", "D", "E", "F"]

    for m in movies_data:
        if m["id"] not in existing_ids:
            cursor.execute("""
            INSERT INTO movies (id, title, genre, language, duration_mins, rating, poster_url, description, director, cast, release_year, backdrop_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                m["id"], m["title"], m["genre"], m["language"], m["duration_mins"], m["rating"],
                m["poster_url"], m["description"], m["director"], m["cast"], m["release_year"], m["backdrop_url"]
            ))

            # Add showtimes for the new movie
            for d_idx, d in enumerate(dates[:2]): # Today and Tomorrow
                for t_idx, theater in enumerate(theaters):
                    slot = time_slots[(sh_counter % len(time_slots))]
                    sh_id = f"sht-{sh_counter}"
                    cursor.execute("""
                    INSERT INTO showtimes (id, movie_id, theater_name, screen_type, screen_number, date, time_slot, base_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sh_id, m["id"], theater["name"], theater["screen"], (t_idx + 1), d, slot, theater["base"]
                    ))
                    new_showtimes.append((sh_id, theater["base"]))
                    sh_counter += 1

    # Seed seats for newly created showtimes
    for sh_id, base_price in new_showtimes:
        seat_index = 0
        for row in rows:
            tier = "VIP" if row in ["A", "B"] else ("Premium" if row in ["C", "D"] else "Standard")
            price = SEAT_TIER_PRICING.get(tier, 15.0)
            for num in range(1, 9):
                seat_id = f"{row}{num}"
                status = "booked" if (seat_index + int(sh_id.split("-")[1])) % 7 == 0 else "available"
                cursor.execute("""
                INSERT INTO seats (showtime_id, seat_id, row, number, tier, price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (sh_id, seat_id, row, num, tier, price, status))
                seat_index += 1

    conn.commit()
    conn.close()
