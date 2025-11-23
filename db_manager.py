#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de base de données SQLite avec chemin sécurisé
VERSION PORTABLE - Compatible Windows/Linux/macOS
Compatible PyInstaller et développement
"""

import sqlite3
import os
from pathlib import Path
import sys


class DatabaseManager:
    """Gère la connexion et le chemin de la base de données"""
    
    _instance = None
    _db_path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize_db_path()
        return cls._instance
    
    def _initialize_db_path(self):
        """Initialise le chemin de la base de données - VERSION PORTABLE"""
        
        # Déterminer le dossier d'exécution
        if getattr(sys, 'frozen', False):
            # Mode PyInstaller : dossier de l'exe
            app_dir = Path(sys.executable).parent
            print("🚀 Mode exécutable détecté")
        else:
            # Mode développement : dossier du projet
            app_dir = Path(__file__).parent
            print("🔧 Mode développement détecté")
        
        print(f"📂 Dossier application: {app_dir}")
        
        # Créer un sous-dossier "data" pour la DB
        data_dir = app_dir / "data"
        
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Dossier données créé: {data_dir}")
        except Exception as e:
            print(f"⚠️ Erreur création dossier: {e}")
            # Fallback : utiliser le même dossier que l'exe
            data_dir = app_dir
            print(f"📁 Fallback: {data_dir}")
        
        # Définir le chemin complet de la base
        self._db_path = str(data_dir / "base.db")
        print(f"💾 Base de données: {self._db_path}")
        
        # Vérifier les permissions
        self._check_permissions(data_dir)
    
    def _check_permissions(self, directory):
        """Vérifie les permissions d'écriture"""
        try:
            test_file = directory / ".write_test"
            test_file.touch()
            test_file.unlink()
            print("✅ Permissions d'écriture OK")
        except Exception as e:
            print(f"❌ Erreur permissions: {e}")
            print("⚠️ L'application pourrait ne pas fonctionner correctement")
    
    def get_connection(self):
        """Retourne une connexion à la base de données"""
        try:
            conn = sqlite3.connect(self._db_path)
            return conn
        except sqlite3.Error as e:
            print(f"❌ Erreur connexion DB: {e}")
            raise
    
    @property
    def db_path(self):
        """Retourne le chemin de la base de données"""
        return self._db_path


# Instance globale
db_manager = DatabaseManager()


def get_db_connection():
    """
    Fonction utilitaire pour obtenir une connexion
    À utiliser partout dans le code à la place de sqlite3.connect("base.db")
    """
    return db_manager.get_connection()


def init_all_tables():
    """
    Initialise toutes les tables avec la structure Supabase
    Compatible SQLite
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("📦 Initialisation des tables...")
        
        # Table User
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS User (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifiant TEXT NOT NULL UNIQUE,
                passwords TEXT NOT NULL,
                nom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                email TEXT NOT NULL,
                telephone TEXT NOT NULL,
                etablissement TEXT NOT NULL,
                titre TEXT NOT NULL,
                theme TEXT DEFAULT 'light',
                language TEXT DEFAULT 'fr',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table Students
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Students (
                nom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                matricule TEXT NOT NULL,
                date_naissance TEXT NOT NULL,
                sexe TEXT NOT NULL,
                classe TEXT NOT NULL,
                etablissement TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(matricule, etablissement)
            )
        """)
        
        # Table Matieres
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Matieres (
                nom TEXT NOT NULL,
                genre TEXT NOT NULL,
                etablissement TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(nom, etablissement)
            )
        """)
        
        # Table Teacher
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Teacher (
                ident TEXT NOT NULL UNIQUE,
                pass TEXT NOT NULL,
                matiere TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table Notes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Notes (
                classe TEXT NOT NULL,
                matricule TEXT NOT NULL,
                matiere TEXT NOT NULL,
                coefficient TEXT NOT NULL,
                note_interrogation TEXT NOT NULL,
                note_devoir TEXT NOT NULL,
                note_composition TEXT NOT NULL,
                moyenne TEXT,
                date_saisie TEXT,
                periode TEXT DEFAULT 'Premier Trimestre',
                statut TEXT DEFAULT 'en_cours',
                date_verrouillage TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(matricule, matiere, classe)
            )
        """)
        
        # Index pour Notes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_periode_statut 
            ON Notes(periode, statut)
        """)
        
        # Table Class
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Class (
                nom TEXT NOT NULL,
                etablissement TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(nom, etablissement)
            )
        """)
        
        # Table Trimestre_moyen_save
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Trimestre_moyen_save (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matricule TEXT NOT NULL,
                moyenne REAL NOT NULL,
                annee_scolaire TEXT NOT NULL,
                periode TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(matricule, annee_scolaire, periode)
            )
        """)
        
        # Table de métadonnées de sync
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_metadata (
                table_name TEXT PRIMARY KEY,
                last_sync TIMESTAMP,
                sync_status TEXT DEFAULT 'pending'
            )
        """)
        
        conn.commit()
        print("✅ Toutes les tables initialisées avec succès")
        
    except Exception as e:
        print(f"❌ Erreur initialisation tables: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
