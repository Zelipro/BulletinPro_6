import flet as ft
from Zeli_Dialog import ZeliDialog2
import sqlite3
import os
import shutil
from pathlib import Path
from time import sleep
import threading
import socket
from datetime import datetime
from db_manager import get_db_connection, db_manager, init_all_tables
from sync_manager import sync_manager

# ==================== GESTIONNAIRE DE CONNEXION & SYNC ====================

class SmartSyncManager:
    """Gestionnaire intelligent de synchronisation avec gestion hors ligne"""
    
    def __init__(self):
        self.is_online = False
        self.pending_syncs = []  # File d'attente des syncs en attente
        self.sync_lock = threading.Lock()
        self.check_connection()
    
    def check_connection(self):
        """Vérifie si Internet est disponible"""
        try:
            # Tente de se connecter à Google DNS
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.is_online = True
            return True
        except OSError:
            self.is_online = False
            return False
    
    def add_pending_sync(self, table_name, filter_col, filter_val, operation_type="upsert"):
        """Ajoute une opération de sync à la file d'attente"""
        with self.sync_lock:
            sync_task = {
                "table": table_name,
                "filter_col": filter_col,
                "filter_val": filter_val,
                "operation": operation_type,
                "timestamp": datetime.now().isoformat()
            }
            self.pending_syncs.append(sync_task)
            print(f"📋 Sync ajoutée en file d'attente: {table_name}")
    
    def execute_pending_syncs(self, callback=None):
        """Exécute toutes les syncs en attente"""
        if not self.check_connection():
            print("❌ Pas de connexion - Impossible de synchroniser")
            return False
        
        with self.sync_lock:
            if not self.pending_syncs:
                print("✅ Aucune sync en attente")
                return True
            
            total = len(self.pending_syncs)
            success_count = 0
            failed_syncs = []
            
            for idx, sync_task in enumerate(self.pending_syncs):
                try:
                    if callback:
                        callback(f"Sync {idx+1}/{total}...")
                    
                    sync_manager.sync_table_to_supabase(
                        sync_task["table"],
                        filter_col=sync_task["filter_col"],
                        filter_val=sync_task["filter_val"]
                    )
                    success_count += 1
                    print(f"✅ Sync réussie: {sync_task['table']}")
                    
                except Exception as e:
                    print(f"❌ Échec sync {sync_task['table']}: {e}")
                    failed_syncs.append(sync_task)
            
            # Garder uniquement les syncs échouées
            self.pending_syncs = failed_syncs
            
            print(f"✅ Synchronisation: {success_count}/{total} réussies")
            return success_count > 0
    
    def sync_now(self, table_name, filter_col, filter_val, callback_success=None, callback_error=None):
        """Tente de synchroniser immédiatement, sinon met en attente"""
        
        if not self.check_connection():
            print(f"🔴 Hors ligne - Sync différée pour {table_name}")
            self.add_pending_sync(table_name, filter_col, filter_val)
            if callback_error:
                callback_error("Hors ligne - Données enregistrées localement")
            return False
        
        try:
            print(f"🔄 Synchronisation en ligne de {table_name}...")
            sync_manager.sync_table_to_supabase(
                table_name,
                filter_col=filter_col,
                filter_val=filter_val
            )
            print(f"✅ Sync réussie: {table_name}")
            if callback_success:
                callback_success()
            return True
            
        except Exception as e:
            print(f"❌ Erreur sync {table_name}: {e}")
            # En cas d'erreur, mettre en attente
            self.add_pending_sync(table_name, filter_col, filter_val)
            if callback_error:
                callback_error(f"Erreur sync: {str(e)}")
            return False
    
    def get_sync_status(self):
        """Retourne le statut de synchronisation"""
        if not self.check_connection():
            pending_count = len(self.pending_syncs)
            return {
                "status": "offline",
                "icon": "🔴",
                "message": f"Hors ligne ({pending_count} sync en attente)" if pending_count > 0 else "Hors ligne",
                "color": ft.Colors.RED
            }
        elif len(self.pending_syncs) > 0:
            return {
                "status": "pending",
                "icon": "🟡",
                "message": f"{len(self.pending_syncs)} sync en attente",
                "color": ft.Colors.ORANGE
            }
        else:
            return {
                "status": "online",
                "icon": "🟢",
                "message": "Connecté - Tout synchronisé",
                "color": ft.Colors.GREEN
            }

# Instance globale
smart_sync = SmartSyncManager()

# ==================== FONCTION PRINCIPALE ====================

def Saisie_Notes(page, Donner):
    """Saisie des notes par le professeur pour sa matière uniquement"""
    Dialog = ZeliDialog2(page)
    
    student_list_dialog = None
    
    # Vérifier que c'est bien un prof
    if Donner.get("role") != "prof":
        Dialog.alert_dialog(
            title="Accès refusé",
            message="Seuls les enseignants peuvent saisir des notes."
        )
        return
    
    def Return(Ident):
        """Récupère une information depuis la table User"""
        con = None
        try:
            con = get_db_connection()
            cur = con.cursor()
            cur.execute(
                f"SELECT {Ident} FROM User WHERE identifiant = ? AND titre = ? AND passwords = ?",
                (Donner.get("ident"), Donner.get("role"), Donner.get("pass"))
            )
            donne = cur.fetchall()
            cur.close()
            return donne
        except Exception as e:
            Dialog.error_toast(f"Erreur de récupération: {str(e)}")
            return []
        finally:
            if con:
                con.close()
    
    def get_teacher_subject():
        """Récupère la matière du professeur"""
        con = None
        try:
            con = get_db_connection()
            cur = con.cursor()
            cur.execute("SELECT matiere FROM Teacher WHERE ident = ?", (Donner.get("ident"),))
            result = cur.fetchone()
            return result[0] if result else None
        except:
            return None
        finally:
            if con:
                con.close()
    
    def load_classes_with_students():
        """Charge les classes qui ont des élèves"""
        Etat = Return("etablissement")
        if not Etat:
            return []
        
        con = None
        try:
            con = get_db_connection()
            cur = con.cursor()
            cur.execute("""
                SELECT DISTINCT classe, COUNT(*) as effectif
                FROM Students 
                WHERE etablissement = ?
                GROUP BY classe
                ORDER BY classe
            """, (Etat[0][0],))
            return cur.fetchall()
        except:
            return []
        finally:
            if con:
                con.close()
    
    def load_students_by_class(classe_nom):
        """Charge tous les élèves d'une classe"""
        Etat = Return("etablissement")
        if not Etat:
            return []
        
        con = None
        try:
            con = get_db_connection()
            cur = con.cursor()
            cur.execute("""
                SELECT * FROM Students 
                WHERE classe = ? AND etablissement = ?
                ORDER BY nom, prenom
            """, (classe_nom, Etat[0][0]))
            return cur.fetchall()
        except:
            return []
        finally:
            if con:
                con.close()
    
    def get_matiere_coefficient(matiere_nom):
        """Récupère le coefficient d'une matière"""
        Etat = Return("etablissement")
        if not Etat:
            return "2"
        
        con = None
        try:
            con = get_db_connection()
            cur = con.cursor()
            # Chercher le coefficient dans la table Matieres
            cur.execute("""
                SELECT coefficient FROM Matieres 
                WHERE nom = ? AND etablissement = ?
            """, (matiere_nom, Etat[0][0]))
            result = cur.fetchone()
            if result and result[0]:
                return str(result[0])
            return "2"
        except Exception as e:
            print(f"⚠️ Erreur récupération coefficient: {e}")
            return "2"
        finally:
            if con:
                con.close()
    
    def check_note_exists(matricule, matiere, classe):
        """Vérifie si une note existe déjà"""
        con = None
        try:
            con = get_db_connection()
            cur = con.cursor()
            
            # S'assurer que la table existe AVEC etablissement
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    classe TEXT NOT NULL,
                    matricule TEXT NOT NULL,
                    matiere TEXT NOT NULL,
                    coefficient TEXT NOT NULL,
                    note_interrogation TEXT NOT NULL,
                    note_devoir TEXT NOT NULL,
                    note_composition TEXT NOT NULL,
                    moyenne TEXT,
                    date_saisie TEXT,
                    etablissement TEXT,
                    updated_at TEXT,
                    UNIQUE(matricule, matiere, classe)
                )
            """)
            con.commit()
            
            # Vérifier si la colonne etablissement existe, sinon l'ajouter
            cur.execute("PRAGMA table_info(Notes)")
            columns = [col[1] for col in cur.fetchall()]
            if 'etablissement' not in columns:
                cur.execute("ALTER TABLE Notes ADD COLUMN etablissement TEXT")
                con.commit()
                print("✅ Colonne 'etablissement' ajoutée à la table Notes")
            
            cur.execute("""
                SELECT * FROM Notes 
                WHERE matricule = ? AND matiere = ? AND classe = ?
            """, (matricule, matiere, classe))
            
            result = cur.fetchone()
            return result
            
        except Exception as e:
            print(f"❌ Erreur check_note_exists: {e}")
            return None
        finally:
            if con:
                con.close()
    
    def calculate_moyenne(note_interro, note_devoir, note_compo):
        """Calcule la moyenne"""
        try:
            interro = float(note_interro) if note_interro else 0
            devoir = float(note_devoir) if note_devoir else 0
            compo = float(note_compo) if note_compo else 0
            
            moyenne = (interro + devoir + (2 * compo)) / 4
            return f"{moyenne:.2f}"
        except:
            return "0.00"
    
    def show_sync_status():
        """Affiche le statut de synchronisation"""
        status = smart_sync.get_sync_status()
        
        status_container = ft.Container(
            content=ft.Row([
                ft.Text(status["icon"], size=16),
                ft.Text(status["message"], size=12, color=status["color"]),
            ], spacing=5),
            bgcolor=f"{status['color']}20",
            padding=8,
            border_radius=5,
        )
        
        return status_container
    
    def force_sync_pending():
        """Force la synchronisation des données en attente"""
        if len(smart_sync.pending_syncs) == 0:
            Dialog.info_toast("Aucune donnée à synchroniser")
            return
        
        loading = Dialog.loading_dialog(
            title="Synchronisation...",
            message="Envoi des données vers le serveur"
        )
        
        def do_sync():
            def update_progress(msg):
                print(msg)
            
            success = smart_sync.execute_pending_syncs(callback=update_progress)
            
            Dialog.close_dialog(loading)
            
            if success:
                Dialog.success_toast("Synchronisation réussie !")
                # Rafraîchir l'affichage
                Saisie_Notes(page, Donner)
            else:
                Dialog.error_toast("Échec de la synchronisation")
        
        threading.Thread(target=do_sync, daemon=True).start()
    
    def show_students_list(classe_nom):
        """Affiche la liste des élèves d'une classe"""
        nonlocal student_list_dialog
        
        # Fermer le dialog principal d'abord
        if main_dialog:
            Dialog.close_dialog(main_dialog)
        
        students = load_students_by_class(classe_nom)
        matiere = get_teacher_subject()
        
        if not matiere:
            Dialog.error_toast("Impossible de récupérer votre matière")
            return
        
        print(f"📚 Chargement de {len(students)} élèves pour la classe {classe_nom}")
        
        # Créer les cartes élèves
        student_cards = []
        for student in students:
            try:
                student_cards.append(create_student_card(student, classe_nom, matiere))
            except Exception as e:
                print(f"❌ Erreur création carte élève: {e}")
                print(f"❌ Erreur création carte élève: {e}")
                continue
        
        if not student_cards:
            student_cards = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PEOPLE, size=60, color=ft.Colors.GREY_400),
                        ft.Text("Aucun élève dans cette classe", size=16, color=ft.Colors.GREY_600),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                    ),
                    padding=30
                )
            ]
        
        # Statistiques
        total_students = len(students)
        notes_saisies = sum(1 for s in students if check_note_exists(s[2], matiere, classe_nom))
        reste = total_students - notes_saisies
        
        print(f"📊 Stats: {total_students} élèves, {notes_saisies} notes saisies, {reste} restantes")
        
        try:
            student_list_dialog = Dialog.custom_dialog(
                title=f"📚 {matiere} - Classe {classe_nom}",
                content=ft.Column([
                    # Statut de synchronisation
                    show_sync_status(),
                    
                    ft.Divider(),
                    
                    # Statistiques
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Column([
                                    ft.Text(f"{total_students}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
                                    ft.Text("Élèves", size=12),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=10,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Column([
                                    ft.Text(f"{notes_saisies}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                                    ft.Text("Saisies", size=12),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=10,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Column([
                                    ft.Text(f"{reste}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE),
                                    ft.Text("Restantes", size=12),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=10,
                                expand=True,
                            ),
                        ]),
                        bgcolor=ft.Colors.BLUE_50,
                        padding=10,
                        border_radius=10,
                    ),
                    
                    ft.Divider(),
                    
                    ft.Text("Cliquez sur un élève pour saisir/modifier ses notes", 
                           size=12, italic=True, color=ft.Colors.GREY_600),
                    
                    # Liste des élèves
                    ft.Container(
                        content=ft.Column(
                            controls=student_cards,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        height=320,
                    ),
                ],
                width=500,
                height=550,
                spacing=10,
                ),
                actions=[
                    ft.TextButton(
                        "Retour",
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: back_to_class_selection()
                    ),
                ] + ([
                    ft.IconButton(
                        icon=ft.Icons.SYNC,
                        icon_color=ft.Colors.BLUE,
                        tooltip="Synchroniser maintenant",
                        on_click=lambda e: force_sync_pending()
                    )
                ] if len(smart_sync.pending_syncs) > 0 else [])
            )
            print("✅ Dialog élèves créé avec succès")
        except Exception as e:
            print(f"❌ Erreur création dialog élèves: {e}")
            import traceback
            traceback.print_exc()
            Dialog.error_toast(f"Erreur d'affichage: {str(e)}")
    
    def back_to_class_selection():
        """Retourne à la sélection de classe"""
        if student_list_dialog:
            Dialog.close_dialog(student_list_dialog)
        Saisie_Notes(page, Donner)
    
    def create_student_card(student, classe_nom, matiere):
        """Crée une carte pour un élève"""
        
        note_exists = check_note_exists(student[2], matiere, classe_nom)
        
        status_icon = ft.Icons.CHECK_CIRCLE if note_exists else ft.Icons.ADD_CIRCLE
        status_color = ft.Colors.GREEN if note_exists else ft.Colors.ORANGE
        status_text = "Notes saisies" if note_exists else "À saisir"
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    # Avatar
                    ft.Container(
                        content=ft.Text(
                            student[0][0].upper(),
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                        width=40,
                        height=40,
                        border_radius=20,
                        bgcolor=ft.Colors.BLUE_400 if 'M' in str(student[4]) else ft.Colors.PINK_400,
                        alignment=ft.alignment.center,
                    ),
                    
                    # Infos
                    ft.Column([
                        ft.Text(
                            f"{student[0]} {student[1]}",
                            size=15,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Text(
                            f"Matricule: {student[2]}",
                            size=12,
                            color=ft.Colors.GREY_700,
                        ),
                    ], spacing=2, expand=True),
                    
                    # Statut
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(status_icon, color=status_color, size=18),
                            ft.Text(status_text, size=11, color=status_color),
                        ], spacing=5),
                        padding=5,
                        border_radius=5,
                        bgcolor=f"{status_color}20",
                    ),
                ], spacing=10),
            ]),
            padding=12,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            ink=True,
            height=70,
            on_click=lambda e, s=student: show_student_notes(s, classe_nom, matiere),
        )
    
    def show_student_notes(student, classe_nom, matiere):
        """Affiche le formulaire de saisie/modification des notes"""
        existing_note = check_note_exists(student[2], matiere, classe_nom)
        
        if existing_note:
            show_existing_notes(student, classe_nom, matiere, existing_note)
        else:
            show_add_notes_form(student, classe_nom, matiere)
    
    def show_existing_notes(student, classe_nom, matiere, existing_note):
        """Affiche les notes existantes avec options de modification/suppression"""
        
        info_dialog = Dialog.custom_dialog(
            title="📋 Notes déjà saisies",
            content=ft.Column([
                ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE, size=50),
                ft.Text(
                    "Les notes de cette matière ont déjà été ajoutées",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Divider(),
                ft.Text(f"Élève : {student[0]} {student[1]}", size=14, weight=ft.FontWeight.BOLD),
                ft.Text(f"Matricule : {student[2]}", size=12),
                ft.Text(f"Classe : {classe_nom}", size=12),
                ft.Text(f"Matière : {matiere}", size=12),
                ft.Divider(),
                ft.Text("Notes actuelles :", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Interrogation :", size=13, width=120),
                            ft.Text(f"{existing_note[5]}/20", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
                        ]),
                        ft.Row([
                            ft.Text("Devoir :", size=13, width=120),
                            ft.Text(f"{existing_note[6]}/20", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                        ]),
                        ft.Row([
                            ft.Text("Composition :", size=13, width=120),
                            ft.Text(f"{existing_note[7]}/20", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE),
                        ]),
                        ft.Divider(),
                        ft.Row([
                            ft.Text("Moyenne :", size=14, width=120, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{existing_note[8]}/20", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                        ]),
                    ]),
                    bgcolor=ft.Colors.BLUE_50,
                    padding=15,
                    border_radius=10,
                ),
            ],
            width=400,
            height=400,
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton(
                    "Fermer",
                    icon=ft.Icons.CLOSE,
                    on_click=lambda e: Dialog.close_dialog(info_dialog)
                ),
                ft.ElevatedButton(
                    "Modifier",
                    icon=ft.Icons.EDIT,
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    on_click=lambda e: modify_notes(info_dialog, student, classe_nom, matiere, existing_note)
                ),
                ft.ElevatedButton(
                    "Supprimer",
                    icon=ft.Icons.DELETE,
                    bgcolor=ft.Colors.RED,
                    color=ft.Colors.WHITE,
                    on_click=lambda e: confirm_delete_notes(info_dialog, student, classe_nom, matiere, existing_note)
                ),
            ]
        )
    
    def confirm_delete_notes(parent_dialog, student, classe_nom, matiere, existing_note):
        """Demande confirmation avant suppression des notes"""
        
        confirm_dialog = Dialog.custom_dialog(
            title="⚠️ Confirmation de suppression",
            content=ft.Column([
                ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.RED, size=50),
                ft.Text(
                    "Êtes-vous sûr de vouloir supprimer ces notes ?",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    f"Élève : {student[0]} {student[1]}",
                    size=14,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    f"Matière : {matiere}",
                    size=14,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "⚠️ Cette action est irréversible !",
                    color=ft.Colors.RED,
                    size=12,
                    italic=True,
                    text_align=ft.TextAlign.CENTER
                )
            ],
            width=400,
            height=220,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15
            ),
            actions=[
                ft.TextButton(
                    "Annuler",
                    on_click=lambda e: Dialog.close_dialog(confirm_dialog)
                ),
                ft.ElevatedButton(
                    "Supprimer",
                    bgcolor=ft.Colors.RED,
                    color=ft.Colors.WHITE,
                    icon=ft.Icons.DELETE_FOREVER,
                    on_click=lambda e: execute_delete_notes(confirm_dialog, parent_dialog, student, classe_nom, matiere)
                ),
            ]
        )
    
    def execute_delete_notes(confirm_dialog, parent_dialog, student, classe_nom, matiere):
        """Exécute la suppression des notes avec sync intelligente"""
        
        loading_dialog = Dialog.loading_dialog(
            title="Suppression en cours...",
            message="Veuillez patienter",
            height=100
        )
        
        def do_delete():
            con = None
            try:
                con = db_manager.get_connection()
                cur = con.cursor()
                
                # 🎯 RÉCUPÉRER L'ÉTABLISSEMENT DU PROF CONNECTÉ
                etablissement = None
                Etat = Return("etablissement")
                if Etat and len(Etat) > 0:
                    etablissement = Etat[0][0]
                    print(f"✅ Établissement du prof: {etablissement}")
                
                # Supprimer local
                cur.execute("""
                    DELETE FROM Notes 
                    WHERE matricule = ? AND matiere = ? AND classe = ?
                """, (student[2], matiere, classe_nom))
                
                con.commit()
                con.close()
                
                # ✅ SYNC INTELLIGENTE AVEC FILTRE SUR ÉTABLISSEMENT
                def on_sync_success():
                    print("✅ Suppression synchronisée en ligne")
                
                def on_sync_error(msg):
                    print(f"⚠️ {msg}")
                
                if etablissement:
                    smart_sync.sync_now(
                        "Notes",
                        filter_col="etablissement",
                        filter_val=etablissement,
                        callback_success=on_sync_success,
                        callback_error=on_sync_error
                    )
                else:
                    print("⚠️ Sync impossible (établissement manquant)")
                
                # Fermer dialogs
                Dialog.close_dialog(loading_dialog)
                Dialog.success_toast("Notes supprimées !")
                Dialog.close_dialog(confirm_dialog)
                Dialog.close_dialog(parent_dialog)
                if student_list_dialog:
                    Dialog.close_dialog(student_list_dialog)
                
                # Rafraîchir
                Saisie_Notes(page, Donner)
                
            except Exception as e:
                Dialog.close_dialog(loading_dialog)
                Dialog.error_toast(f"Erreur: {str(e)}")
                print(f"❌ Erreur suppression: {e}")
                import traceback
                traceback.print_exc()
                if con:
                    con.close()
        
        threading.Thread(target=do_delete, daemon=True).start()
    
    def modify_notes(parent_dialog, student, classe_nom, matiere, existing_note):
        """Ouvre le formulaire de modification des notes"""
        Dialog.close_dialog(parent_dialog)
        show_add_notes_form(student, classe_nom, matiere, existing_note)
    
    def show_add_notes_form(student, classe_nom, matiere, existing_note=None):
        """Affiche le formulaire d'ajout/modification des notes"""
        
        is_modification = existing_note is not None
        coefficient = get_matiere_coefficient(matiere)
        
        # Champs de saisie
        coef_field = ft.TextField(
            label="Coefficient",
            value=existing_note[4] if existing_note else coefficient,
            width=150,
            text_align="center",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        interro_field = ft.TextField(
            label="Note Interrogation (/20)",
            value=existing_note[5] if existing_note else "",
            hint_text="0-20",
            width=200,
            text_align="center",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.QUIZ,
        )
        
        devoir_field = ft.TextField(
            label="Note Devoir (/20)",
            value=existing_note[6] if existing_note else "",
            hint_text="0-20",
            width=200,
            text_align="center",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.ASSIGNMENT,
        )
        
        compo_field = ft.TextField(
            label="Note Composition (/20)",
            value=existing_note[7] if existing_note else "",
            hint_text="0-20",
            width=200,
            text_align="center",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.ASSIGNMENT_TURNED_IN,
        )
        
        moyenne_display = ft.Text(
            "Moyenne : --/20",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.RED,
        )
        
        def update_moyenne(e):
            """Met à jour la moyenne en temps réel"""
            try:
                moy = calculate_moyenne(
                    interro_field.value,
                    devoir_field.value,
                    compo_field.value
                )
                moyenne_display.value = f"Moyenne : {moy}/20"
                moyenne_display.color = ft.Colors.GREEN if float(moy) >= 10 else ft.Colors.RED
            except:
                moyenne_display.value = "Moyenne : --/20"
                moyenne_display.color = ft.Colors.RED
            page.update()
        
        interro_field.on_change = update_moyenne
        devoir_field.on_change = update_moyenne
        compo_field.on_change = update_moyenne
        
        if existing_note:
            update_moyenne(None)
        
        # Variable pour empêcher double-clic
        is_saving = [False]
        
        def validate_and_save(e):
            """Valide et enregistre les notes"""
            
            # ✅ Empêcher double-clic
            if is_saving[0]:
                return
            
            # Validation
            errors = []
            
            if not interro_field.value or not interro_field.value.strip():
                interro_field.error_text = "Note requise"
                errors.append("interro")
            else:
                try:
                    note = float(interro_field.value)
                    if note < 0 or note > 20:
                        interro_field.error_text = "Note entre 0 et 20"
                        errors.append("interro")
                    else:
                        interro_field.error_text = None
                except:
                    interro_field.error_text = "Note invalide"
                    errors.append("interro")
            
            if not devoir_field.value or not devoir_field.value.strip():
                devoir_field.error_text = "Note requise"
                errors.append("devoir")
            else:
                try:
                    note = float(devoir_field.value)
                    if note < 0 or note > 20:
                        devoir_field.error_text = "Note entre 0 et 20"
                        errors.append("devoir")
                    else:
                        devoir_field.error_text = None
                except:
                    devoir_field.error_text = "Note invalide"
                    errors.append("devoir")
            
            if not compo_field.value or not compo_field.value.strip():
                compo_field.error_text = "Note requise"
                errors.append("compo")
            else:
                try:
                    note = float(compo_field.value)
                    if note < 0 or note > 20:
                        compo_field.error_text = "Note entre 0 et 20"
                        errors.append("compo")
                    else:
                        compo_field.error_text = None
                except:
                    compo_field.error_text = "Note invalide"
                    errors.append("compo")
            
            if errors:
                page.update()
                return
            
            # Marquer comme en cours de sauvegarde
            is_saving[0] = True
            
            # Enregistrer
            save_notes(
                student[2],
                classe_nom,
                matiere,
                coef_field.value,
                interro_field.value,
                devoir_field.value,
                compo_field.value,
                is_modification
            )
        
        def save_notes(matricule, classe, matiere, coef, interro, devoir, compo, is_update):
            """Enregistre les notes avec sync intelligente"""
            
            loading_dialog = Dialog.loading_dialog(
                title="Enregistrement en cours...",
                message="Veuillez patienter",
                height=100
            )
            
            def do_save():
                con = None
                try:
                    con = db_manager.get_connection()
                    cur = con.cursor()
                    
                    # 🎯 RÉCUPÉRER L'ÉTABLISSEMENT DU PROF CONNECTÉ
                    etablissement = None
                    Etat = Return("etablissement")
                    if Etat and len(Etat) > 0:
                        etablissement = Etat[0][0]
                        print(f"✅ Établissement du prof: {etablissement}")
                    else:
                        print("⚠️ Impossible de récupérer l'établissement du prof")
                    
                    # Calculer moyenne et dates
                    moyenne = calculate_moyenne(interro, devoir, compo)
                    date_saisie = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    updated_at = datetime.now().isoformat()
                    
                    if is_update:
                        cur.execute("""
                            UPDATE Notes 
                            SET coefficient = ?,
                                note_interrogation = ?,
                                note_devoir = ?,
                                note_composition = ?,
                                moyenne = ?,
                                date_saisie = ?,
                                etablissement = ?,
                                updated_at = ?
                            WHERE matricule = ? AND matiere = ? AND classe = ?
                        """, (coef, interro, devoir, compo, moyenne, date_saisie, etablissement, updated_at, matricule, matiere, classe))
                        message = "Notes modifiées avec succès !"
                    else:
                        cur.execute("""
                            INSERT INTO Notes 
                            (classe, matricule, matiere, coefficient, note_interrogation, 
                             note_devoir, note_composition, moyenne, date_saisie, etablissement, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (classe, matricule, matiere, coef, interro, devoir, compo, moyenne, date_saisie, etablissement, updated_at))
                        message = "Notes enregistrées avec succès !"
                    
                    con.commit()
                    con.close()
                    
                    # ✅ SYNC INTELLIGENTE AVEC FILTRE SUR ÉTABLISSEMENT
                    sync_message = ""
                    
                    def on_sync_success():
                        nonlocal sync_message
                        sync_message = "✅ Synchronisé en ligne"
                    
                    def on_sync_error(msg):
                        nonlocal sync_message
                        sync_message = f"⚠️ Sauvegardé localement ({msg})"
                    
                    if etablissement:
                        smart_sync.sync_now(
                            "Notes",
                            filter_col="etablissement",
                            filter_val=etablissement,
                            callback_success=on_sync_success,
                            callback_error=on_sync_error
                        )
                    else:
                        sync_message = "⚠️ Sync impossible (établissement manquant)"
                    
                    # Fermer loading
                    Dialog.close_dialog(loading_dialog)
                    
                    # Dialog de succès
                    success_dialog = Dialog.custom_dialog(
                        title="✅ Succès",
                        content=ft.Column([
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=60),
                            ft.Text(message, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                            ft.Text(sync_message, size=12, italic=True) if sync_message else ft.Container(),
                            ft.Divider(),
                            ft.Container(
                                content=ft.Column([
                                    ft.Text(f"Élève : {student[0]} {student[1]}", size=14),
                                    ft.Text(f"Matière : {matiere}", size=14),
                                    ft.Text(f"Moyenne obtenue : {moyenne}/20", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                                ]),
                                bgcolor=ft.Colors.GREEN_50,
                                padding=15,
                                border_radius=10,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                        width=400,
                        height=280,
                        ),
                        actions=[
                            ft.ElevatedButton(
                                "OK",
                                bgcolor=ft.Colors.GREEN,
                                color=ft.Colors.WHITE,
                                on_click=lambda e: close_all_and_refresh(success_dialog, notes_dialog)
                            )
                        ]
                    )
                    
                    # Réinitialiser le flag
                    is_saving[0] = False
                    
                except Exception as e:
                    Dialog.close_dialog(loading_dialog)
                    Dialog.error_toast(f"Erreur: {str(e)}")
                    print(f"❌ Erreur sauvegarde: {e}")
                    import traceback
                    traceback.print_exc()
                    is_saving[0] = False
                    if con:
                        con.close()
            
            threading.Thread(target=do_save, daemon=True).start()
        
        def close_all_and_refresh(success_dialog, notes_dialog):
            """Ferme tous les dialogs et rafraîchit"""
            Dialog.close_dialog(success_dialog)
            Dialog.close_dialog(notes_dialog)
            if student_list_dialog:
                Dialog.close_dialog(student_list_dialog)
            Saisie_Notes(page, Donner)
        
        # Dialog de saisie
        notes_dialog = Dialog.custom_dialog(
            title=f"📝 {'Modification' if is_modification else 'Saisie'} des notes - {matiere}",
            content=ft.Column([
                # Infos élève
                ft.Container(
                    content=ft.Column([
                        ft.Text("Informations de l'élève", size=16, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.Text("Nom complet :", size=13, width=120),
                            ft.Text(f"{student[0]} {student[1]}", size=13, weight=ft.FontWeight.BOLD),
                        ]),
                        ft.Row([
                            ft.Text("Matricule :", size=13, width=120),
                            ft.Text(f"{student[2]}", size=13, weight=ft.FontWeight.BOLD),
                        ]),
                        ft.Row([
                            ft.Text("Classe :", size=13, width=120),
                            ft.Text(f"{classe_nom}", size=13, weight=ft.FontWeight.BOLD),
                        ]),
                        ft.Row([
                            ft.Text("Matière :", size=13, width=120),
                            ft.Text(f"{matiere}", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                        ]),
                    ]),
                    bgcolor=ft.Colors.BLUE_50,
                    padding=15,
                    border_radius=10,
                ),
                
                ft.Divider(),
                
                coef_field,
                ft.Divider(),
                
                ft.Text("Saisie des notes", size=16, weight=ft.FontWeight.BOLD),
                interro_field,
                devoir_field,
                compo_field,
                
                ft.Divider(),
                
                ft.Container(
                    content=moyenne_display,
                    bgcolor=ft.Colors.YELLOW_50,
                    padding=10,
                    border_radius=10,
                    alignment=ft.alignment.center,
                ),
            ],
            width=450,
            height=500,
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions=[
                ft.TextButton(
                    "Annuler",
                    icon=ft.Icons.CLOSE,
                    on_click=lambda e: Dialog.close_dialog(notes_dialog)
                ),
                ft.ElevatedButton(
                    "Enregistrer",
                    icon=ft.Icons.SAVE,
                    bgcolor=ft.Colors.GREEN,
                    color=ft.Colors.WHITE,
                    on_click=validate_and_save
                ),
            ]
        )
    
    def create_class_card(classe):
        """Crée une carte pour une classe"""
        classe_nom = classe[0]
        effectif = classe[1]
        
        matiere = get_teacher_subject()
        
        notes_count = 0
        if matiere:
            con = None
            try:
                con = get_db_connection()
                cur = con.cursor()
                cur.execute("""
                    SELECT COUNT(*) FROM Notes 
                    WHERE classe = ? AND matiere = ?
                """, (classe_nom, matiere))
                result = cur.fetchone()
                notes_count = result[0] if result else 0
            except Exception as e:
                print(f"❌ Erreur comptage notes: {e}")
            finally:
                if con:
                    con.close()
        
        pourcentage = int((notes_count / effectif * 100)) if effectif > 0 else 0
        
        if pourcentage == 100:
            progress_color = ft.Colors.GREEN
        elif pourcentage >= 50:
            progress_color = ft.Colors.ORANGE
        else:
            progress_color = ft.Colors.RED
        
        def on_class_click(e):
            """Gestion du clic sur une classe"""
            print(f"🖱️ Clic sur classe: {classe_nom}")
            try:
                show_students_list(classe_nom)
            except Exception as error:
                print(f"❌ Erreur lors du clic: {error}")
                import traceback
                traceback.print_exc()
                Dialog.error_toast(f"Erreur: {str(error)}")
        
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.CLASS_, color=ft.Colors.BLUE, size=40),
                ft.Text(
                    classe_nom,
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=5),
                ft.Row([
                    ft.Icon(ft.Icons.PEOPLE, color=ft.Colors.BLUE, size=20),
                    ft.Text(f"{effectif} élève(s)", size=14),
                ],
                alignment=ft.MainAxisAlignment.CENTER
                ),
                ft.Container(height=5),
                ft.Column([
                    ft.Text(f"{notes_count}/{effectif} notes saisies", 
                           size=12, color=ft.Colors.GREY_700),
                    ft.ProgressBar(
                        value=pourcentage / 100,
                        color=progress_color,
                        bgcolor=ft.Colors.GREY_300,
                        height=8,
                    ),
                    ft.Text(f"{pourcentage}%", size=12, 
                           weight=ft.FontWeight.BOLD, color=progress_color),
                ],
                spacing=3,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5,
            alignment=ft.MainAxisAlignment.CENTER,
            ),
            border=ft.border.all(2, ft.Colors.BLUE_200),
            border_radius=15,
            padding=20,
            margin=10,
            width=220,
            height=220,
            ink=True,
            on_click=on_class_click,
        )
    
    # ==================== DIALOGUE PRINCIPAL ====================
    
    teacher_subject = get_teacher_subject()
    
    if not teacher_subject:
        Dialog.alert_dialog(
            title="Erreur",
            message="Impossible de récupérer votre matière d'enseignement."
        )
        return
    
    print(f"📘 Matière du professeur: {teacher_subject}")
    
    classes = load_classes_with_students()
    print(f"📚 Classes chargées: {len(classes)}")
    
    class_cards = []
    for classe in classes:
        try:
            card = create_class_card(classe)
            class_cards.append(card)
            print(f"✅ Carte créée pour classe: {classe[0]}")
        except Exception as e:
            print(f"❌ Erreur création carte classe {classe[0]}: {e}")
            import traceback
            traceback.print_exc()
    
    if not class_cards:
        class_cards = [
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.CLASS_, size=60, color=ft.Colors.GREY_400),
                    ft.Text(
                        "Aucune classe disponible",
                        size=16,
                        color=ft.Colors.GREY_600
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
                ),
                padding=30
            )
        ]
    
    # Boutons d'actions - Ne jamais mettre None dans la liste !
    action_buttons = [
        ft.TextButton(
            "Fermer",
            icon=ft.Icons.CLOSE,
            on_click=lambda e: Dialog.close_dialog(main_dialog)
        )
    ]
    
    # Ajouter bouton de sync si nécessaire
    if len(smart_sync.pending_syncs) > 0:
        action_buttons.insert(0, ft.ElevatedButton(
            f"Synchroniser ({len(smart_sync.pending_syncs)})",
            icon=ft.Icons.CLOUD_UPLOAD,
            bgcolor=ft.Colors.ORANGE,
            color=ft.Colors.WHITE,
            on_click=lambda e: force_sync_pending()
        ))
    
    main_dialog = Dialog.custom_dialog(
        title=f"📝 Saisie des notes - {teacher_subject}",
        content=ft.Column([
            # Statut de connexion
            show_sync_status(),
            
            ft.Divider(),
            
            # Infos prof
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.PERSON, color=ft.Colors.PURPLE, size=30),
                        ft.Column([
                            ft.Text(
                                f"Prof : {Donner.get('name', 'Enseignant')}",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                f"Matière : {teacher_subject}",
                                size=14,
                                color=ft.Colors.PURPLE,
                                weight=ft.FontWeight.W_500
                            ),
                        ], spacing=2),
                    ], spacing=10),
                ]),
                bgcolor=ft.Colors.PURPLE_50,
                padding=15,
                border_radius=10,
            ),
            
            ft.Divider(),
            
            ft.Text(
                "Sélectionnez une classe pour saisir les notes",
                size=14,
                italic=True,
                color=ft.Colors.GREY_600,
                text_align=ft.TextAlign.CENTER
            ),
            
            ft.Container(height=5),
            
            # Grille des classes
            ft.Container(
                content=ft.GridView(
                    controls=class_cards,
                    runs_count=2,
                    max_extent=240,
                    child_aspect_ratio=1.0,
                    spacing=10,
                    run_spacing=10,
                ),
                height=320,
            ),
        ],
        width=550,
        height=550,
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        actions=action_buttons
    )
