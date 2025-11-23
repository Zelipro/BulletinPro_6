import sqlite3
import threading
import time
from datetime import datetime
from supabase import create_client, Client
from typing import Optional, Dict, Any
import json

from config import SUPABASE_URL, SUPABASE_KEY, SYNC_INTERVAL
from db_manager import get_db_connection, init_all_tables


class SyncManager:
    """Gestionnaire de synchronisation entre SQLite local et Supabase"""
    
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.sync_thread: Optional[threading.Thread] = None
        self.is_syncing = False
        self.last_sync: Optional[datetime] = None
        
    # ============ CONNEXION & INITIALISATION ============
    
    def get_local_connection(self):
        """Obtenir une connexion à la base locale"""
        return get_db_connection()
    
    def init_local_tables(self):
        """Initialise les tables locales avec structure Supabase complète"""
        init_all_tables()
    
    # ============ SYNC AU LOGIN ============
    
    def sync_on_login(self, callback=None):
        """
        Synchronisation lors de la connexion
        1. Charge TOUS les Users
        """
        try:
            print("🔄 Sync au login - Chargement Users...")
            
            # Charger tous les users et des prof
            self.sync_table_from_supabase("User")
            self.sync_table_from_supabase("Teacher")
            
            if callback:
                callback("Users chargés")
            
            print("✅ Sync login terminé")
            return True
            
        except Exception as e:
            print(f"❌ Erreur sync login: {e}")
            return False
    
    def sync_etablissement_data(self, etablissement: str, callback=None):
        """
        Charge toutes les données d'un établissement spécifique
        """
        try:
            print(f"🔄 Chargement données: {etablissement}")
            
            tables = ["Students", "Matieres", "Teacher", "Notes", "Class"]
            
            for table in tables:
                if callback:
                    callback(f"Chargement {table}...")
                
                self.sync_table_from_supabase(
                    table, 
                    filter_col="etablissement",
                    filter_val=etablissement
                )
            
            print(f"✅ Données {etablissement} chargées")
            return True
            
        except Exception as e:
            print(f"❌ Erreur sync établissement: {e}")
            return False
    
    # ============ SYNC TABLES ============
    
    def sync_table_from_supabase(self, table_name: str, 
                                  filter_col: str = None, 
                                  filter_val: str = None):
        """
        Synchronise une table depuis Supabase vers local
        ✅ IMPORTANT: Ignore les colonnes 'id' de Supabase
        """
        try:
            # Récupérer depuis Supabase
            query = self.supabase.table(table_name).select("*")
            
            if filter_col and filter_val:
                query = query.eq(filter_col, filter_val)
            
            response = query.execute()
            remote_data = response.data
            
            if not remote_data:
                print(f"ℹ️ Aucune donnée pour {table_name}")
                return
            
            # Insérer/Mettre à jour en local
            conn = self.get_local_connection()
            cursor = conn.cursor()
            
            for row in remote_data:
                # ✅ SUPPRIMER 'id' DE SUPABASE (on n'en a pas besoin localement)
                row_data = {k: v for k, v in row.items() if k != 'id'}
                
                # Mettre à jour updated_at
                row_data['updated_at'] = datetime.now().isoformat()
                
                # Déterminer la clé unique selon la table
                if table_name == "User":
                    unique_check = "identifiant = ?"
                    unique_val = (row_data.get('identifiant'),)
                elif table_name == "Students":
                    unique_check = "matricule = ? AND etablissement = ?"
                    unique_val = (row_data.get('matricule'), row_data.get('etablissement'))
                elif table_name == "Notes":
                    unique_check = "matricule = ? AND matiere = ? AND classe = ?"
                    unique_val = (row_data.get('matricule'), row_data.get('matiere'), row_data.get('classe'))
                elif table_name in ["Matieres", "Class"]:
                    unique_check = "nom = ? AND etablissement = ?"
                    unique_val = (row_data.get('nom'), row_data.get('etablissement'))
                elif table_name == "Teacher":
                    unique_check = "ident = ?"
                    unique_val = (row_data.get('ident'),)
                elif table_name == "Trimestre_moyen_save":
                    unique_check = "matricule = ? AND annee_scolaire = ? AND periode = ?"
                    unique_val = (row_data.get('matricule'), row_data.get('annee_scolaire'), row_data.get('periode'))
                else:
                    unique_check = None
                
                if unique_check:
                    # Vérifier si la ligne existe déjà
                    cursor.execute(f"SELECT 1 FROM {table_name} WHERE {unique_check}", unique_val)
                    exists = cursor.fetchone()
                    
                    if exists:
                        # UPDATE
                        set_clause = ', '.join([f"{k} = ?" for k in row_data.keys()])
                        values = list(row_data.values()) + list(unique_val)
                        cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE {unique_check}", values)
                    else:
                        # INSERT
                        columns = ', '.join(row_data.keys())
                        placeholders = ', '.join(['?' for _ in row_data])
                        cursor.execute(
                            f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                            list(row_data.values())
                        )
                else:
                    # INSERT simple
                    columns = ', '.join(row_data.keys())
                    placeholders = ', '.join(['?' for _ in row_data])
                    cursor.execute(
                        f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                        list(row_data.values())
                    )
            
            conn.commit()
            conn.close()
            
            print(f"✅ {table_name}: {len(remote_data)} lignes synchronisées")
            
        except Exception as e:
            print(f"❌ Erreur sync {table_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def sync_table_to_supabase(self, table_name: str, 
                               filter_col: str = None, 
                               filter_val: str = None):
        """
        Synchronise une table depuis local vers Supabase
        ✅ IMPORTANT: N'envoie QUE les colonnes existantes (sans 'id')
        """
        try:
            conn = self.get_local_connection()
            cursor = conn.cursor()
            
            # Récupérer données locales modifiées
            query = f"SELECT * FROM {table_name}"
            params = []
            
            if filter_col and filter_val:
                query += f" WHERE {filter_col} = ?"
                params.append(filter_val)
            
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            local_data = cursor.fetchall()
            
            conn.close()
            
            if not local_data:
                print(f"ℹ️ Aucune donnée à syncer pour {table_name}")
                return
            
            synced_count = 0
            skipped_count = 0
            
            for row in local_data:
                row_dict = dict(zip(columns, row))
                
                # ✅ Supprimer 'id' local avant d'envoyer à Supabase
                local_id = row_dict.pop('id', None)
                
                # Mettre à jour updated_at
                row_dict['updated_at'] = datetime.now().isoformat()
                
                try:
                    # Utiliser upsert pour gérer les doublons
                    self.supabase.table(table_name).upsert(row_dict).execute()
                    synced_count += 1
                    
                except Exception as e:
                    # Si c'est un doublon, ignorer et continuer
                    if 'duplicate key' in str(e).lower() or '23505' in str(e):
                        print(f"⚠️ Doublon ignoré dans {table_name}")
                        skipped_count += 1
                    else:
                        print(f"❌ Erreur upsert: {e}")
                        raise
            
            print(f"✅ {table_name}: {synced_count} synced, {skipped_count} doublons ignorés")
            
        except Exception as e:
            print(f"❌ Erreur sync vers Supabase {table_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # ============ SYNC AUTOMATIQUE ============
    
    def start_auto_sync(self, etablissement: str):
        """Démarre la synchronisation automatique"""
        if self.is_syncing:
            print("⚠️ Sync déjà en cours")
            return
        
        self.is_syncing = True
        
        def sync_loop():
            while self.is_syncing:
                try:
                    print(f"🔄 Sync auto - {datetime.now()}")
                    
                    tables = ["Students", "Matieres", "Teacher", "Notes", "Class", "User"]
                    
                    for table in tables:
                        if table == "User":
                            self.sync_table_from_supabase(table)
                            self.sync_table_to_supabase(table)
                        else:
                            self.sync_table_from_supabase(
                                table,
                                filter_col="etablissement",
                                filter_val=etablissement
                            )
                            self.sync_table_to_supabase(
                                table,
                                filter_col="etablissement",
                                filter_val=etablissement
                            )
                    
                    self.last_sync = datetime.now()
                    print(f"✅ Sync auto terminé - {self.last_sync}")
                    
                except Exception as e:
                    print(f"❌ Erreur sync auto: {e}")
                
                time.sleep(SYNC_INTERVAL)
        
        self.sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self.sync_thread.start()
        print("✅ Sync automatique démarré")
    
    def stop_auto_sync(self):
        """Arrête la synchronisation automatique"""
        self.is_syncing = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        print("🛑 Sync automatique arrêté")


# Instance globale
sync_manager = SyncManager()
