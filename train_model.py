import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import pickle

data = {
    "description": [
        # Food
        "Starbucks", "McDonalds", "KFC", "Pizza Hut", "Subway",
        "Burger King", "Dominos", "Dunkin Donuts", "Chipotle", "Taco Bell",
        "Chick fil A", "Olive Garden", "Applebees", "Panera Bread", "Five Guys",
        "Sushi Restaurant", "Chinese Food", "Indian Restaurant", "Thai Food", "Italian Restaurant",
        "Grocery Store", "Whole Foods", "Trader Joes", "Aldi", "Lidl",
        # Transport
        "Shell Gas Station", "BP Gas", "Uber", "Lyft", "Bus Ticket",
        "Chevron", "Exxon", "Mobil", "Train Ticket", "Metro Card",
        "Parking Fee", "Toll Fee", "Car Wash", "Auto Repair", "Jiffy Lube",
        "Delta Airlines", "United Airlines", "American Airlines", "Ryanair", "Easyjet",
        "Rental Car", "Hertz", "Enterprise Rent", "Avis Car", "Taxi Cab",
        # Entertainment
        "Netflix", "Spotify", "Cinema", "PlayStation", "Steam",
        "Disney Plus", "HBO Max", "Amazon Prime", "Apple TV", "Hulu",
        "Concert Tickets", "Theater Tickets", "Museum Entry", "Zoo Entry", "Amusement Park",
        "Xbox Game Pass", "Nintendo Switch", "Board Game", "Bowling Alley", "Mini Golf",
        "Escape Room", "Laser Tag", "Arcade Games", "Comedy Club", "Sports Event",
        # Shopping
        "Walmart", "Amazon", "Ikea", "Target", "Ebay",
        "Best Buy", "Apple Store", "Samsung Store", "Home Depot", "Lowes",
        "Zara", "HM", "Nike Store", "Adidas Store", "Forever 21",
        "Macys", "Nordstrom", "Gap", "Old Navy", "Uniqlo",
        "Etsy", "Shein", "Fashion Nova", "Foot Locker", "Sports Direct",
        # Bills
        "Electric Bill", "Water Bill", "Internet Bill", "Rent", "Phone Bill",
        "Gas Bill", "Cable TV Bill", "Insurance Payment", "Mortgage Payment", "HOA Fee",
        "Car Insurance", "Health Insurance", "Life Insurance", "Home Insurance", "Renters Insurance",
        "Netflix Subscription", "Spotify Subscription", "iCloud Storage", "Google One", "Adobe Creative",
        "Gym Membership", "Amazon Prime Subscription", "Microsoft 365", "Dropbox", "VPN Service",
        # Health
        "Pharmacy", "Hospital", "Doctor", "Dentist", "Optician",
        "CVS Pharmacy", "Walgreens", "Rite Aid", "Vitamin Shoppe", "GNC",
        "Therapist", "Chiropractor", "Physical Therapy", "Lab Test", "MRI Scan",
        "Urgent Care", "Emergency Room", "Specialist Visit", "Eye Exam", "Blood Test",
        "Gym", "Yoga Studio", "Pilates", "Personal Trainer", "Meditation App",
        # Education
        "Udemy", "Coursera", "Skillshare", "LinkedIn Learning", "Pluralsight",
        "Tuition Fee", "School Books", "University Fee", "Online Course", "Bootcamp",
        "Duolingo", "Chegg", "Khan Academy", "Tutoring Service", "Study Materials",
        "Textbooks", "School Supplies", "Student Loan", "Library Fee", "Workshop Fee",
        # Travel
        "Hotel Stay", "Airbnb", "Booking com", "Expedia", "Hotels com",
        "Hilton Hotel", "Marriott Hotel", "Holiday Inn", "Hostel", "Resort Fee",
        "Travel Insurance", "Visa Fee", "Passport Fee", "Airport Parking", "Airport Transfer",
        "Cruise Booking", "Tour Package", "Travel Agency", "Luggage Fee", "Currency Exchange",
    ],
    "category": [
        # Food (25)
        "Food", "Food", "Food", "Food", "Food",
        "Food", "Food", "Food", "Food", "Food",
        "Food", "Food", "Food", "Food", "Food",
        "Food", "Food", "Food", "Food", "Food",
        "Food", "Food", "Food", "Food", "Food",
        # Transport (25)
        "Transport", "Transport", "Transport", "Transport", "Transport",
        "Transport", "Transport", "Transport", "Transport", "Transport",
        "Transport", "Transport", "Transport", "Transport", "Transport",
        "Transport", "Transport", "Transport", "Transport", "Transport",
        "Transport", "Transport", "Transport", "Transport", "Transport",
        # Entertainment (25)
        "Entertainment", "Entertainment", "Entertainment", "Entertainment", "Entertainment",
        "Entertainment", "Entertainment", "Entertainment", "Entertainment", "Entertainment",
        "Entertainment", "Entertainment", "Entertainment", "Entertainment", "Entertainment",
        "Entertainment", "Entertainment", "Entertainment", "Entertainment", "Entertainment",
        "Entertainment", "Entertainment", "Entertainment", "Entertainment", "Entertainment",
        # Shopping (25)
        "Shopping", "Shopping", "Shopping", "Shopping", "Shopping",
        "Shopping", "Shopping", "Shopping", "Shopping", "Shopping",
        "Shopping", "Shopping", "Shopping", "Shopping", "Shopping",
        "Shopping", "Shopping", "Shopping", "Shopping", "Shopping",
        "Shopping", "Shopping", "Shopping", "Shopping", "Shopping",
        # Bills (25)
        "Bills", "Bills", "Bills", "Bills", "Bills",
        "Bills", "Bills", "Bills", "Bills", "Bills",
        "Bills", "Bills", "Bills", "Bills", "Bills",
        "Bills", "Bills", "Bills", "Bills", "Bills",
        "Bills", "Bills", "Bills", "Bills", "Bills",
        # Health (25)
        "Health", "Health", "Health", "Health", "Health",
        "Health", "Health", "Health", "Health", "Health",
        "Health", "Health", "Health", "Health", "Health",
        "Health", "Health", "Health", "Health", "Health",
        "Health", "Health", "Health", "Health", "Health",
        # Education (20)
        "Education", "Education", "Education", "Education", "Education",
        "Education", "Education", "Education", "Education", "Education",
        "Education", "Education", "Education", "Education", "Education",
        "Education", "Education", "Education", "Education", "Education",
        # Travel (20)
        "Travel", "Travel", "Travel", "Travel", "Travel",
        "Travel", "Travel", "Travel", "Travel", "Travel",
        "Travel", "Travel", "Travel", "Travel", "Travel",
        "Travel", "Travel", "Travel", "Travel", "Travel",
    ]
}

df = pd.DataFrame(data)

pipeline = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("clf", LogisticRegression())
])

pipeline.fit(df["description"], df["category"])

with open("model.pkl", "wb") as f:
    pickle.dump(pipeline, f)

print("Model trained and saved to model.pkl")