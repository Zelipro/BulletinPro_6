import os
from dotenv import load_dotenv

# Charger .env seulement en développement
if os.path.exists('.env'):
    load_dotenv()

# Utiliser des variables d'environnement avec fallback
SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://fumkblfluoswkcegpape.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ1bWtibGZsdW9zd2tjZWdwYXBlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIwOTIyODgsImV4cCI6MjA3NzY2ODI4OH0.9s8cpr-jxaoqAZdBhUKlSHsjrqX-2zFr14y11RipmVA"

LOCAL_DB = "base.db"
SYNC_INTERVAL = 600