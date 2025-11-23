import flet as ft
from Zeli_Dialog import ZeliDialog2
import sqlite3
import os
import shutil
from pathlib import Path
from time import sleep
from db_manager import get_db_connection

def Gestion_Eleve(page, Donner , view_only=False):
    Dialog = ZeliDialog2(page)

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
    
    def load_student():
        """Charge la liste de tous les eleves de l'établissement"""
        Etat = Return("etablissement")
        
        if not Etat:
            return []
        
        #Vue que les etudiants ne sont pas des user on les met dans une Autre base de donné
        con = None
        try:
            con = get_db_connection() #Connection de la base de donné
            #===== AU cas ou la base de donner n'est pas encore creer creons la ====
            cur = con.cursor()
            cur.execute(f"CREATE TABLE IF NOT EXISTS Students(nom TEXT NOT NULL , prenom TEXT NOT NULL , matricule TEXT NOT NULL , date_naissance TEXT NOT NULL , sexe TEXT NOT NULL , classe TEXT NOT NULL,etablissement TEXT NOT NULL)")
            con.commit()
            cur.close()
            #=======================================================
            
            #======================== Selection des etudiant ========#==
            cur = con.cursor()
            cur.execute("SELECT * FROM Students WHERE etablissement = ?",(Etat[0][0],))
            donne = cur.fetchall()
            #======================================
            return donne
        except Exception as e:
            Dialog.error_toast(f"Erreur de chargement: {str(e)}")
            return []
        finally:
            if con:
                con.close()
    
    def add_student():
        """Ajoute un nouvel enseignant"""
        
        # Champs de saisie
        nom_field = ft.TextField(
            label="Nom",
            hint_text="Entrez le nom",
            autofocus=True,
            capitalization=ft.TextCapitalization.WORDS
        )
        prenom_field = ft.TextField(
            label="Prénom",
            hint_text="Entrez le prénom",
            capitalization=ft.TextCapitalization.WORDS
        )
        matricule_field = ft.TextField(
            label="matricule",
            hint_text="XXXXX",
            keyboard_type=ft.KeyboardType.NUMBER
        )
        borndate_field = ft.TextField(
            label="date_naissance",
            hint_text="31/10/2025",
            keyboard_type=ft.KeyboardType.PHONE
        )
        sexe_dropdown = ft.Dropdown(
            label="Sexe",
            hint_text="Sélectionnez le sexe",
            options=[
                ft.dropdown.Option("Masculin(M)",leading_icon=ft.Icons.MAN),
                ft.dropdown.Option("Feminin(F)",leading_icon=ft.Icons.WOMAN),

            ]
        )
        
        Etat = Return("etablissement")
        Menu = []
        
        if not Etat:
            return 
        
        con = None
        try:
            con = get_db_connection()
            cur = con.cursor()
            
            #==== Create la table si elle n'existe pas =====
            cur.execute("CREATE TABLE IF NOT EXISTS Class(nom TEXT NOT NULL , etablissement TEXT NOT NULL)")
            con.commit()
            #===============================================
            cur.close()
            
            #====== Verifier si la classe que l'on veux ajouter existe deja
            cur = con.cursor()
            cur.execute("SELECT * FROM Class WHERE etablissement = ?",(Etat[0][0],))

            for elmt in cur.fetchall():
                Menu.append(
                    ft.dropdown.Option(elmt[0]),
                )
            
            cur.close()
            #===========================================================

        except Exception as ex:
            Dialog.error_toast(f"Erreut de recharge : {ex}")
            return
        
        finally:
            if con:
                con.close()
                    
        classe_dropdown = ft.Dropdown(
            label="classe",
            hint_text="Sélectionnez la classe",
            options=Menu,
        )
        
        def clear_errors():
            """Efface tous les messages d'erreur"""
            for field in [nom_field, prenom_field, matricule_field, borndate_field, sexe_dropdown , classe_dropdown]:
                field.error_text = None
            page.update()
        
        def validate_fields():
            """Valide tous les champs"""
            is_valid = True
            
            # Validation des champs texte
            for field in [nom_field, prenom_field, matricule_field, borndate_field, sexe_dropdown , classe_dropdown]:
                if not field.value or not field.value.strip():
                    field.error_text = "Ce champ est obligatoire"
                    is_valid = False
                else:
                    field.error_text = None
            page.update()
            return is_valid
        
        def save_student(e):
            """Enregistre l'enseignant"""
            clear_errors()
            
            if not validate_fields():
                return
            
            con = None
            try:
                # Récupération établissement
                etablissement_data = Return("etablissement")
                if not etablissement_data or not etablissement_data[0]:
                    Dialog.error_toast("Impossible de récupérer l'établissement")
                    return
                
                etablissement = etablissement_data[0][0]

                con = get_db_connection()
                cur = con.cursor()
                
                # Vérification si existe dans User
                cur.execute(
                    "SELECT * FROM Students WHERE etablissement = ? AND matricule = ? AND nom = ? AND prenom = ?",
                    (etablissement,matricule_field.value,nom_field.value,prenom_field.value)
                )
                if cur.fetchone():
                    nom_field.error_text = "L'élève existe déjà"
                    prenom_field.error_text = "L'élève existe déjà"
                    page.update()
                    return
                
                # Insertion dans Student
                cur.execute("""
                    INSERT INTO Students (nom, prenom, matricule, date_naissance, sexe ,classe , etablissement)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    nom_field.value,
                    prenom_field.value,
                    matricule_field.value,
                    borndate_field.value,
                    sexe_dropdown.value,
                    classe_dropdown.value,
                    etablissement
                ))
                con.commit()
            
                # NOUVEAU : Sync vers Supabase
                try:
                    from sync_manager import sync_manager
                    sync_manager.sync_table_to_supabase(
                        "Students",
                        filter_col="etablissement",
                        filter_val=etablissement
                    )
                except Exception as e:
                    Dialog.error_toast(f"⚠️ Erreur sync: {e}")
                    
                Dialog.alert_dialog(title = "Notification",message="Eleve ajouté avec success !")
                
            except Exception as ex:
                Dialog.error_toast(f"Erreur d'ajout: {str(ex)}")
            finally:
                if con:
                    con.close()

        def close_all_and_refresh(success_dialog, main_dialog):
            """Ferme tous les dialogs et rafraîchit"""
            Dialog.close_dialog(success_dialog)
            Dialog.close_dialog(main_dialog)
            refresh_display()
        
        # Dialog principal d'ajout
        DIag2 = Dialog.custom_dialog(
            title="➕ Nouvel Eleve",
            content=ft.Column([
                nom_field,
                prenom_field,
                matricule_field,
                borndate_field,
                sexe_dropdown,
                classe_dropdown,
            ],
            width=400,
            height=350,
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions=[
                ft.TextButton(
                    "Annuler",
                    icon=ft.Icons.CLOSE,
                    on_click=lambda e: Dialog.close_dialog(DIag2)
                ),
                ft.ElevatedButton(
                    "Enregistrer",
                    icon=ft.Icons.SAVE,
                    bgcolor=ft.Colors.GREEN,
                    color=ft.Colors.WHITE,
                    on_click=save_student
                ),
            ]
        )
    
    def show_details(student):
        """Affiche les détails d'un eleve"""
        detail_dialog = Dialog.custom_dialog(
            title=f"📋 Détails - {student[0]} {student[1]}",
            content=ft.Column([
                ft.Divider(),
                create_info_row("Nom:", student[0]),
                create_info_row("Prénom:", student[1]),
                create_info_row("matricule:", student[2]),
                create_info_row("date_naissance:", student[3]),
                create_info_row("sexe:", student[4]),
                create_info_row("classe:", student[5]),
                ft.Divider(),
            ],
            width=450,
            height=350,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            spacing=10,
            ),
            actions=[
                ft.TextButton(
                    "Fermer",
                    icon=ft.Icons.CLOSE,
                    icon_color=ft.Colors.RED,
                    on_click=lambda e: Dialog.close_dialog(detail_dialog)
                )
            ]
        )
    
    def create_info_row(label, value):
        """Crée une ligne d'information"""
        return ft.Row([
            ft.Text(label, size=15, weight=ft.FontWeight.BOLD, width=150),
            ft.Text(str(value or "N/A"), size=15, selectable=True, expand=True),
        ], spacing=10)
    
    def edit_student(student):
        """Modifie un eleve"""
        name_field = ft.TextField(label="Non", value=student[0])
        prenom_field = ft.TextField(label="Prénom", value=student[1])
        matricule_field = ft.TextField(label="matricule", value=student[2], read_only=True, disabled=True)
        borndate_field = ft.TextField(label="date_naissance", value=student[3])
        sexe_field = ft.TextField(label="sexe", value=student[4])
        classe_field = ft.TextField(label="classe", value=student[5])
        etabl_field = ft.TextField(label="classe", value=student[6], read_only=True, disabled=True)
        
        
        def save_changes(e, dialog):
            con = None
            try:
                con = get_db_connection()
                cur = con.cursor()
                
                cur.execute("""
                    UPDATE Students 
                    SET nom = ?, prenom = ?, date_naissance = ? ,sexe = ?,classe = ? 
                    WHERE matricule = ? AND etablissement = ?
                """, (
                    name_field.value,
                    prenom_field.value,
                    borndate_field.value,
                    sexe_field.value,
                    classe_field.value,
                    matricule_field.value,
                    etabl_field.value,
                ))
                con.commit()
                
                # NOUVEAU : Sync vers Supabase
                try:
                    from sync_manager import sync_manager
                    sync_manager.sync_table_to_supabase(
                        "Students",
                        filter_col="etablissement",
                        filter_val=etabl_field.value
                    )
                except Exception as e:
                    Dialog.error_toast(f"⚠️ Erreur sync: {e}")
                    
                Dialog.info_toast("Modifications enregistrées !")
                Dialog.close_dialog(dialog)
                refresh_display()
                
            except sqlite3.Error as e:
                Dialog.error_toast(f"Erreur: {str(e)}")
            finally:
                if con:
                    con.close()
        
        edit_dialog = Dialog.custom_dialog(
            title=f"✏️ Modifier - {student[0]} {student[1]}",
            content=ft.Column([
                name_field,
                prenom_field,
                borndate_field,
                sexe_field,
                classe_field,
                matricule_field,
                etabl_field,
            ],
            width=400,
            height=380,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10
            ),
            actions=[
                ft.TextButton(
                    "Annuler",
                    on_click=lambda e: Dialog.close_dialog(edit_dialog)
                ),
                ft.ElevatedButton(
                    "Enregistrer",
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    on_click=lambda e: save_changes(e, edit_dialog)
                )
            ]
        )
    
    def confirm_delete(student):
        """Demande confirmation avant suppression"""
        confirm_dialog = Dialog.custom_dialog(
            title="⚠️ Confirmation de suppression",
            content=ft.Column([
                ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.RED, size=50),
                ft.Text(
                    "Êtes-vous sûr de vouloir supprimer cet eleve?",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    f"Eleve: {student[3]} {student[4]}",
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
                    on_click=lambda e: execute_delete(student, confirm_dialog)
                )
            ]
        )
    
    def execute_delete(student, dialog):
        """Exécute la suppression"""
        con = None
        try:
            con = get_db_connection()
            cur = con.cursor()
            
            # Suppression de User
            cur.execute("DELETE FROM Students WHERE nom = ? AND prenom = ?  AND matricule = ? AND etablissement = ?", (student[0],student[1],student[2],student[6]))
            
            con.commit()
            
            # NOUVEAU : Sync vers Supabase
            try:
                from sync_manager import sync_manager
                sync_manager.sync_table_to_supabase(
                    "Students",
                    filter_col="etablissement",
                    filter_val=student[6]
                )
            except Exception as e:
                Dialog.error_toast(f"⚠️ Erreur sync: {e}")
                
            Dialog.info_toast("Eleve supprimé !")
            Dialog.close_dialog(dialog)
            refresh_display()
            
        except sqlite3.Error as e:
            Dialog.error_toast(f"Erreur de suppression: {str(e)}")
        finally:
            if con:
                con.close()
    
    def refresh_display():
        """Rafraîchit l'affichage de la liste"""
        Dialog.close_dialog(main_dialog)
        # Réouvre le dialog avec les données à jour
        Gestion_Eleve(page, Donner, Dialog)
    
    def create_student_card(student):
        """Crée une carte pour un enseignant"""
        return ft.Container(
            content=ft.Column([
                ft.Text(
                    f"{student[0]} {student[1]}",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(f"Classe :{student[5]}", size = 15),
                ft.Text(f"Matricue :{student[2]}", size=15),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.INFO,
                        tooltip="Détails",
                        icon_color=ft.Colors.BLUE,
                        on_click=lambda e, t=student: show_details(t)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Modifier",
                        icon_color=ft.Colors.GREEN,
                        on_click=lambda e, t=student: edit_student(t)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        tooltip="Supprimer",
                        icon_color=ft.Colors.RED,
                        on_click=lambda e, t=student: confirm_delete(t)
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8
            ),
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=ft.border_radius.only(top_right=20, bottom_left=20),
            padding=20,
            margin=10,
            
            width=280,
            height=200,
            #bgcolor=ft.Colors.ON_SURFACE_VARIANT,
        )
    
    # Chargement des enseignants
    students = load_student()
    student_cards = [create_student_card(student) for student in students]
    
    # Si aucun enseignant
    if not student_cards:
        student_cards = [
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SCHOOL, size=60, color=ft.Colors.GREY_400),
                    ft.Text(
                        "Aucun Eleve trouvé",
                        size=16,
                        color=ft.Colors.GREY_600
                    ),
                    ft.Text(
                        "Cliquez sur 'Ajouter' pour commencer",
                        size=12,
                        color=ft.Colors.GREY_500
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
                ),
                padding=30
            )
        ]
    
    # Dialog principal
    main_dialog = Dialog.custom_dialog(
        title=f"👨‍🏫 Liste des élèves ({len(students)})",
        content=ft.Column([
            ft.Row(
                [
                    ft.Column(
                        controls=student_cards,
                        scroll=ft.ScrollMode.AUTO,
                        height=330,
                        width = 350,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            ft.Container(expand=True),
            ft.Divider(),
            ft.ElevatedButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ADD, color=ft.Colors.WHITE),
                    ft.Text("Ajouter un élève", color=ft.Colors.WHITE),
                ], spacing=8),
                bgcolor=ft.Colors.GREEN_700,
                on_click=lambda e: add_student(),
            )
        ],
        width=450,
        height=450,
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
    

def Gestion_Eleve_Liste(page, Donner):
    Dialog = ZeliDialog2(page)

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
    
    def load_student():
        """Charge la liste de tous les eleves de l'établissement"""
        Etat = Return("etablissement")
        
        if not Etat:
            return []
        
        #Vue que les etudiants ne sont pas des user on les met dans une Autre base de donné
        con = None
        try:
            con = get_db_connection() #Connection de la base de donné
            #===== AU cas ou la base de donner n'est pas encore creer creons la ====
            cur = con.cursor()
            cur.execute(f"CREATE TABLE IF NOT EXISTS Students(nom TEXT NOT NULL , prenom TEXT NOT NULL , matricule TEXT NOT NULL , date_naissance TEXT NOT NULL , sexe TEXT NOT NULL , classe TEXT NOT NULL,etablissement TEXT NOT NULL)")
            con.commit()
            cur.close()
            #=======================================================
            
            #======================== Selection des etudiant ========#==
            cur = con.cursor()
            cur.execute("SELECT * FROM Students WHERE etablissement = ?",(Etat[0][0],))
            donne = cur.fetchall()
            #======================================
            return donne
        except Exception as e:
            Dialog.error_toast(f"Erreur de chargement: {str(e)}")
            return []
        finally:
            if con:
                con.close()
    
    def Close(d):
        d.open = False
        page.update()
        Gestion_Eleve_Liste(page, Donner)
        
    def create_info_row(label, value):
        """Crée une ligne d'information"""
        return ft.Row([
            ft.Text(label, size=15, weight=ft.FontWeight.BOLD, width=150),
            ft.Text(str(value or "N/A"), size=15, selectable=True, expand=True),
        ], spacing=10)
                      
    def show_details(student):
        """Affiche les détails d'un eleve"""
        detail_dialog = Dialog.custom_dialog(
            title=f"📋 Détails - {student[0]} {student[1]}",
            content=ft.Column([
                ft.Divider(),
                create_info_row("Nom:", student[0]),
                create_info_row("Prénom:", student[1]),
                create_info_row("matricule:", student[2]),
                create_info_row("date_naissance:", student[3]),
                create_info_row("sexe:", student[4]),
                create_info_row("classe:", student[5]),
                ft.Divider(),
            ],
            width=450,
            height=350,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            spacing=10,
            ),
            actions=[
                ft.TextButton(
                    "Fermer",
                    icon=ft.Icons.CLOSE,
                    icon_color=ft.Colors.RED,
                    on_click=lambda e: Close(detail_dialog)
                )
            ]
        )
    def create_student_card(student):
        """Crée une carte pour un enseignant"""
        return ft.Container(
            content=ft.Column([
                ft.Text(
                    f"{student[0]} {student[1]}",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(f"Classe :{student[5]}", size = 15),
                ft.Text(f"Matricue :{student[2]}", size=15),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.INFO,
                        tooltip="Détails",
                        icon_color=ft.Colors.BLUE,
                        on_click=lambda e, t=student: show_details(t)
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8
            ),
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=ft.border_radius.only(top_right=20, bottom_left=20),
            padding=20,
            margin=10,
            
            width=280,
            height=200,
            #bgcolor=ft.Colors.ON_SURFACE_VARIANT,
        )
        
    # Chargement des enseignants
    students = load_student()
    student_cards = [create_student_card(student) for student in students]
    
    # Si aucun enseignant
    if not student_cards:
        student_cards = [
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SCHOOL, size=60, color=ft.Colors.GREY_400),
                    ft.Text(
                        "Aucun Eleve trouvé",
                        size=16,
                        color=ft.Colors.GREY_600
                    ),
                    ft.Text(
                        "Cliquez sur 'Ajouter' pour commencer",
                        size=12,
                        color=ft.Colors.GREY_500
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
                ),
                padding=30
            )
        ]
    
    # Dialog principal
    main_dialog = Dialog.custom_dialog(
        title=f"👨‍🏫 Liste des élèves ({len(students)})",
        content=ft.Column([
            ft.Row(
                [
                    ft.Column(
                        controls=student_cards,
                        scroll=ft.ScrollMode.AUTO,
                        height=330,
                        width = 350,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            ft.Container(expand=True),
        ],
        width=450,
        height=450,
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
    
