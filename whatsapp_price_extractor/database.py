# database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import pymysql
import pandas as pd

# --- Pour utiliser pymysql comme connecteur MySQL/MariaDB ---
pymysql.install_as_MySQLdb()

# --- Définition du modèle de base ---
Base = declarative_base()
DB_USER = "root"
DB_PASS = "root"
DB_HOST = "localhost"
DB_NAME = "db_extraction"


engine = create_engine(
    f"mysql+mysqldb://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4",
    # echo=True
)

# === Modeles ===
class Message(Base):
    __tablename__ = 'messages'
    message_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    sender = Column(String(255), nullable=False)
    message = Column(Text, nullable=False) 

from sqlalchemy import Text

class Price(Base):
    __tablename__ = 'prices'
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    animal_type = Column(String(255), nullable=False)
    action_type = Column(String(255))
    extraction_method = Column(String(255))

# --- Création des tables dans MariaDB ---
Base.metadata.create_all(engine)

# --- Session ---
Session = sessionmaker(bind=engine)
session = Session()

# === Fonctions d'ajout ===
def add_message(session, message_data):
    if not message_data.get('date') or not message_data.get('sender') or not message_data.get('message'):
        print("⚠️ Données message incomplètes:", message_data)
        return None

    exists = session.query(Message).filter_by(
        date=message_data['date'],
        sender=message_data['sender'],
        message=message_data['message']
    ).first()

    if exists:
        # print("ℹ️ Message déjà existant en BD:", message_data['message'][:50])
        return exists

    msg = Message(**message_data)
    session.add(msg)
    try:
        session.commit()
        # print(" Message ajouté:", message_data['message'][:50])
    except IntegrityError as e:
        session.rollback()
        # print("❌ Erreur ajout message:", e)
        return session.query(Message).filter_by(
            date=message_data['date'],
            sender=message_data['sender'],
            message=message_data['message']
        ).first()
    return msg

def add_price(session, price_data):
    if not price_data.get('message_id') or not price_data.get('price') or not price_data.get('animal_type'):
        print(" Données prix incomplètes:", price_data)
        return None

    exists = session.query(Price).filter_by(
        message_id=price_data['message_id'],
        price=price_data['price'],
        animal_type=price_data['animal_type']
    ).first()

    if exists:
        # print("ℹ️ Prix déjà existant en BD:", price_data)
        return exists

    price_entry = Price(**price_data)
    session.add(price_entry)
    try:
        session.commit()
        print("✅ Prix ajouté:", price_data)
    except IntegrityError as e:
        session.rollback()
        print("❌ Erreur ajout prix:", e)
        return session.query(Price).filter_by(
            message_id=price_data['message_id'],
            price=price_data['price'],
            animal_type=price_data['animal_type']
        ).first()
    return price_entry

# === Debug tables ===
def print_tables():
    print("\n--- Messages en BD ---")
    for msg in session.query(Message).all():
        print(msg.message_id, msg.date, msg.sender, msg.message[:50])

    print("\n--- Prices en BD ---")
    for p in session.query(Price).all():
        print(p.id, p.message_id, p.price, p.animal_type, p.action_type)

# === Exemple d'utilisation ===
if __name__ == "__main__":
    # Exemple message
    message_data = {
        'date': datetime.now(),
        'sender': '+22670123456',
        'message': "Exemple de message pour test MariaDB"
    }
    msg = add_message(session, message_data)

    price_data = {
        'message_id': msg.message_id,
        'price': 10000,
        'animal_type': 'porcelet',
        'action_type': 'vente',
        'extraction_method': 'manual'
    }
    add_price(session, price_data)

    # Affiche tables
    print_tables()



def get_prices_dataframe(session):
    """
    Récupère toutes les données nécessaires depuis la BD
    et renvoie un DataFrame prêt pour le modèle.
    """
    # Jointure Messages <-> Prices
    query = session.query(
        Price.id.label("price_id"),
        Price.price,
        Price.animal_type,
        Price.action_type,
        Message.date,
        Message.sender,
        Message.message
    ).join(Message, Price.message_id == Message.message_id)
    
    # Transformation en DataFrame
    df = pd.read_sql(query.statement, session.bind)
    
    #'date' est bien datetime
    df['date'] = pd.to_datetime(df['date'])
    
    return df
   
