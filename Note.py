import flet as ft
from Zeli_Dialog import ZeliDialog2
import sqlite3
import os
import shutil
from pathlib import Path
from time import sleep
from db_manager import get_db_connection
from db_manager import get_db_connection, db_manager, init_all_tables

def Saisie_Notes(page, Donner):
    """Saisie des notes par le professeur pour sa matière uniquement"""
    Dialog = ZeliDialog2(page)
    
    # ✅ IMPORTANT: Déclarer student_list_dialog GLOBALEMENT en haut
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
            return "2"
        except:
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
                    UNIQUE(matricule, matiere, classe)
                )
            """)
            con.commit()
            
            cur.execute("""
                SELECT * FROM Notes 
                WHERE matricule = ? AND matiere = ? AND classe = ?
            """, (matricule, matiere, classe))
            
            result = cur.fetchone()
            return result
            
        except:
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
    
    # ✅ DÉPLACER show_students_list ICI (avant create_student_card)
    def show_students_list(classe_nom):
        """Affiche la liste des élèves d'une classe"""
        nonlocal student_list_dialog  # ✅ Utiliser nonlocal pour modifier la variable
        
        students = load_students_by_class(classe_nom)
        matiere = get_teacher_subject()
        
        if not matiere:
            Dialog.error_toast("Impossible de récupérer votre matière")
            return
        
        # Créer les cartes élèves
        student_cards = []
        for student in students:
            student_cards.append(create_student_card(student, classe_nom, matiere))
        
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
        
        student_list_dialog = Dialog.custom_dialog(
            title=f"📚 {matiere} - Classe {classe_nom}",
            content=ft.Column([
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
                    height=350,
                ),
            ],
            width=500,
            height=500,
            spacing=10,
            ),
            actions=[
                ft.TextButton(
                    "Retour",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: back_to_class_selection()
                )
            ]
        )
    
    def back_to_class_selection():
        """Retourne à la sélection de classe"""
        if student_list_dialog:
            Dialog.close_dialog(student_list_dialog)
        # Recharger la page principale
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
    
    # Reste du code (show_student_notes, etc.)
    # ... [GARDER TOUT LE RESTE DU CODE INCHANGÉ]
    
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
                )
            ]
        )
    
    def execute_delete_notes(confirm_dialog, parent_dialog, student, classe_nom, matiere):
        """Exécute la suppression des notes"""
        con = None
        try:
            con = db_manager.get_connection()
            cur = con.cursor()
            
            cur.execute("""
                DELETE FROM Notes 
                WHERE matricule = ? AND matiere = ? AND classe = ?
            """, (student[2], matiere, classe_nom))
            
            con.commit()
            
            # NOUVEAU : Sync vers Supabase
            try:
                from sync_manager import sync_manager
                # Récupérer établissement
                cur.execute("SELECT etablissement FROM Students WHERE matricule = ?", (student[2],))
                result = cur.fetchone()
                if result:
                    sync_manager.sync_table_to_supabase(
                        "Notes",
                        filter_col="classe",
                        filter_val=classe_nom
                    )
            except Exception as e:
                Dialog.error_toast(f"⚠️ Erreur sync: {e}")
            
            Dialog.info_toast("Notes supprimées avec succès !")
            Dialog.close_dialog(confirm_dialog)
            Dialog.close_dialog(parent_dialog)
            Dialog.close_dialog(student_list_dialog)
            
            # Réouvrir la sélection de classe
            Saisie_Notes(page, Donner)
            
        except sqlite3.Error as e:
            Dialog.error_toast(f"Erreur de suppression: {str(e)}")
        finally:
            if con:
                con.close()
    
    def modify_notes(parent_dialog, student, classe_nom, matiere, existing_note):
        """Ouvre le formulaire de modification des notes"""
        Dialog.close_dialog(parent_dialog)
        show_add_notes_form(student, classe_nom, matiere, existing_note)
    
    def show_add_notes_form(student, classe_nom, matiere, existing_note=None):
        """Affiche le formulaire d'ajout/modification des notes"""
        
        is_modification = existing_note is not None
        
        # Récupérer le coefficient
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
        
        # Lier les changements
        interro_field.on_change = update_moyenne
        devoir_field.on_change = update_moyenne
        compo_field.on_change = update_moyenne
        
        # Calculer la moyenne initiale si modification
        if existing_note:
            update_moyenne(None)
        
        def validate_and_save(e):
            """Valide et enregistre les notes"""
            
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
            
            # Enregistrer
            save_notes(
                student[2],  # matricule
                classe_nom,
                matiere,
                coef_field.value,
                interro_field.value,
                devoir_field.value,
                compo_field.value,
                is_modification
            )
        
        def save_notes(matricule, classe, matiere, coef, interro, devoir, compo, is_update):
            """Enregistre les notes dans la base de données"""
            con = None
            try:
                con = db_manager.get_connection()
                cur = con.cursor()
                
                # Calculer la moyenne
                moyenne = calculate_moyenne(interro, devoir, compo)
                
                # Date de saisie
                from datetime import datetime
                date_saisie = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if is_update:
                    # Mise à jour
                    cur.execute("""
                        UPDATE Notes 
                        SET coefficient = ?,
                            note_interrogation = ?,
                            note_devoir = ?,
                            note_composition = ?,
                            moyenne = ?,
                            date_saisie = ?
                        WHERE matricule = ? AND matiere = ? AND classe = ?
                    """, (coef, interro, devoir, compo, moyenne, date_saisie, matricule, matiere, classe))
                    
                    message = "Notes modifiées avec succès !"
                else:
                    # Insertion
                    cur.execute("""
                        INSERT INTO Notes 
                        (classe, matricule, matiere, coefficient, note_interrogation, 
                         note_devoir, note_composition, moyenne, date_saisie)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (classe, matricule, matiere, coef, interro, devoir, compo, moyenne, date_saisie))
                    
                    message = "Notes enregistrées avec succès !"
                
                con.commit()
                
                # NOUVEAU : Sync vers Supabase
                try:
                    from sync_manager import sync_manager
                    # Récupérer établissement depuis Students
                    cur.execute("SELECT etablissement FROM Students WHERE matricule = ?", (matricule,))
                    result = cur.fetchone()
                    if result:
                        sync_manager.sync_table_to_supabase(
                            "Notes",
                            filter_col="classe",
                            filter_val=classe
                        )
                except Exception as e:
                    Dialog.error_toast(f"⚠️ Erreur sync: {e}")
                    
                # Dialog de succès
                success_dialog = Dialog.custom_dialog(
                    title="✅ Succès",
                    content=ft.Column([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=60),
                        ft.Text(message, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
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
                    height=250,
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
                
            except sqlite3.Error as e:
                Dialog.error_toast(f"Erreur d'enregistrement: {str(e)}")
            finally:
                if con:
                    con.close()
        
        def close_all_and_refresh(success_dialog, notes_dialog):
            """Ferme tous les dialogs et rafraîchit"""
            Dialog.close_dialog(success_dialog)
            Dialog.close_dialog(notes_dialog)
            Dialog.close_dialog(student_list_dialog)
            
            # Réouvrir la sélection de classe
            Saisie_Notes(page, Donner)
        
        # Dialog de saisie des notes
        notes_dialog = Dialog.custom_dialog(
            title=f"📝 {'Modification' if is_modification else 'Saisie'} des notes - {matiere}",
            content=ft.Column([
                # Informations élève
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
                
                # Coefficient
                coef_field,
                
                ft.Divider(),
                
                # Notes
                ft.Text("Saisie des notes", size=16, weight=ft.FontWeight.BOLD),
                interro_field,
                devoir_field,
                compo_field,
                
                ft.Divider(),
                
                # Moyenne
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
    
    def create_student_card(student, classe_nom, matiere):
        """Crée une carte pour un élève"""
        
        # Vérifier si des notes existent
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
    
    def show_students_list(classe_nom):
        """Affiche la liste des élèves d'une classe"""
        global student_list_dialog
        
        students = load_students_by_class(classe_nom)
        matiere = get_teacher_subject()
        
        if not matiere:
            Dialog.error_toast("Impossible de récupérer votre matière")
            return
        
        # Créer les cartes élèves
        student_cards = [
            create_student_card(student, classe_nom, matiere)
            for student in students
        ]
        
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
        
        student_list_dialog = Dialog.custom_dialog(
            title=f"📚 {matiere} - Classe {classe_nom}",
            content=ft.Column([
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
                
                ft.Text("Cliquez sur un élève pour saisir/modifier ses notes", size=12, italic=True, color=ft.Colors.GREY_600),
                
                # Liste des élèves
                ft.Container(
                    content=ft.Column(
                        controls=student_cards,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    height=350,
                ),
            ],
            width=500,
            height=500,
            spacing=10,
            ),
            actions=[
                ft.TextButton(
                    "Retour",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: back_to_class_selection()
                )
            ]
        )
    
    def back_to_class_selection():
        """Retourne à la sélection de classe"""
        Dialog.close_dialog(student_list_dialog)
        Saisie_Notes(page, Donner)
        
    # ✅ Ajouter toutes les autres fonctions ici...
    # (show_existing_notes, modify_notes, show_add_notes_form, etc.)
    # Je les ai omises pour la clarté, mais gardez-les toutes !
    
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
            except:
                pass
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
            on_click=lambda e, c=classe_nom: show_students_list(c),  # ✅ Maintenant ça marche !
        )
    
    # ==================== DIALOGUE PRINCIPAL ====================
    
    teacher_subject = get_teacher_subject()
    
    if not teacher_subject:
        Dialog.alert_dialog(
            title="Erreur",
            message="Impossible de récupérer votre matière d'enseignement."
        )
        return
    
    classes = load_classes_with_students()
    
    class_cards = [create_class_card(classe) for classe in classes]
    
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
    
    main_dialog = Dialog.custom_dialog(
        title=f"📝 Saisie des notes - {teacher_subject}",
        content=ft.Column([
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
            
            ft.Container(
                content=ft.GridView(
                    controls=class_cards,
                    runs_count=2,
                    max_extent=240,
                    child_aspect_ratio=1.0,
                    spacing=10,
                    run_spacing=10,
                ),
                height=350,
            ),
        ],
        width=550,
        height=500,
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        actions=[
            ft.TextButton(
                "Fermer",
                icon=ft.Icons.CLOSE,
                on_click=lambda e: Dialog.close_dialog(main_dialog)
            )
        ]
    )
