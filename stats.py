import flet as ft
from Zeli_Dialog import ZeliDialog2
import sqlite3
import os
import shutil
from pathlib import Path
from time import sleep
from db_manager import get_db_connection

def Stats(page, Donner=None):
    """Statistiques selon le type d'utilisateur (creator/admin)
    - Creator : Voit uniquement les ADMINS (établissements)
    - Admin : Voit uniquement les PROFS de son établissement
    - Prof : N'A PAS accès aux stats
    """
    Dialog = ZeliDialog2(page)
    
    # Définir les informations par défaut pour le créateur
    if not Donner:
        Donner = {
            "ident": "Deg",
            "role": "creator",
            "pass": None,
            "name": "Développeur"
        }
    
    # Les profs n'ont pas accès aux stats
    if Donner.get("role") == "prof":
        Dialog.alert_dialog(
            title="Accès refusé",
            message="Les enseignants n'ont pas accès aux statistiques."
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
    
    def create_info_row(label, value):
        """Crée une ligne d'information"""
        return ft.Row([
            ft.Text(label, size=15, weight=ft.FontWeight.BOLD, width=150),
            ft.Text(str(value or "N/A"), size=15, selectable=True, expand=True),
        ], spacing=10)
    
    # ==================== FONCTIONS POUR CREATOR (voir les admins) ====================
    def load_all_admins():
        """Charge tous les administrateurs"""
        con = None
        try:
            con = get_db_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM User WHERE titre = 'admin'")
            return cur.fetchall()
        except sqlite3.Error:
            return []
        finally:
            if con:
                con.close()
    
    def show_admin_details(admin):
        """Affiche les détails d'un administrateur"""
        detail_dialog = Dialog.custom_dialog(
            title=f"📋 Détails Admin - {admin[3]} {admin[4]}",
            content=ft.Column([
                ft.Divider(),
                create_info_row("Nom:", admin[3]),
                create_info_row("Prénom:", admin[4]),
                create_info_row("Identifiant:", admin[1]),
                create_info_row("Mot de passe:", admin[2]),
                create_info_row("Email:", admin[5]),
                create_info_row("Téléphone:", admin[6]),
                create_info_row("Établissement:", admin[7]),
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
    
    def edit_admin(admin):
        """Modifie un administrateur"""
        name_field = ft.TextField(label="Nom", value=admin[3])
        prenom_field = ft.TextField(label="Prénom", value=admin[4])
        ident_field = ft.TextField(label="Identifiant", value=admin[1], read_only=True, disabled=True)
        pass_field = ft.TextField(label="Mot de passe", value=admin[2])
        email_field = ft.TextField(label="Email", value=admin[5])
        tele_field = ft.TextField(label="Téléphone", value=admin[6])
        etabl_field = ft.TextField(label="Établissement", value=admin[7])
        
        def save_changes(e, dialog):
            con = None
            try:
                con = get_db_connection()

                cur = con.cursor()
                
                cur.execute("""
                    UPDATE User 
                    SET nom = ?, passwords = ?, prenom = ?, email = ?, telephone = ?, etablissement = ?
                    WHERE identifiant = ? AND titre = 'admin'
                """, (
                    name_field.value.strip(),
                    pass_field.value,
                    prenom_field.value.strip(),
                    email_field.value.strip(),
                    tele_field.value.strip(),
                    etabl_field.value.strip(),
                    ident_field.value
                ))
                con.commit()
                
                Dialog.info_toast("Modifications enregistrées !")
                Dialog.close_dialog(dialog)
                Dialog.close_dialog(main_dialog)
                Stats(page, Donner)  # Rafraîchir
                
            except sqlite3.Error as e:
                Dialog.error_toast(f"Erreur: {str(e)}")
            finally:
                if con:
                    con.close()
        
        edit_dialog = Dialog.custom_dialog(
            title=f"✏️ Modifier - {admin[3]} {admin[4]}",
            content=ft.Column([
                name_field,
                prenom_field,
                ident_field,
                pass_field,
                email_field,
                tele_field,
                etabl_field,
            ],
            width=400,
            height=380,
            scroll=ft.ScrollMode.AUTO,
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
    
    def confirm_delete_admin(admin):
        """Demande confirmation avant suppression d'un admin"""
        confirm_dialog = Dialog.custom_dialog(
            title="⚠️ Confirmation de suppression",
            content=ft.Column([
                ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.RED, size=50),
                ft.Text(
                    "Êtes-vous sûr de vouloir supprimer cet administrateur ?",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    f"Admin: {admin[3]} {admin[4]}",
                    size=14,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    f"Établissement: {admin[7]}",
                    size=12,
                    color=ft.Colors.GREY_700,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "⚠️ Cette action supprimera uniquement cet administrateur.\n"
                    "Les enseignants et données de l'établissement seront conservés.",
                    color=ft.Colors.ORANGE,
                    size=12,
                    italic=True,
                    text_align=ft.TextAlign.CENTER
                )
            ],
            width=400,
            height=250,
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
                    on_click=lambda e: execute_delete_admin(admin, confirm_dialog)
                )
            ]
        )
    
    def confirm_delete_school(admin):
        """Demande confirmation avant suppression d'un établissement entier"""
        confirm_dialog = Dialog.custom_dialog(
            title="⚠️ Suppression d'établissement",
            content=ft.Column([
                ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.RED, size=50),
                ft.Text(
                    "ATTENTION : Suppression totale de l'établissement !",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.RED
                ),
                ft.Text(
                    f"Établissement: {admin[7]}",
                    size=14,
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text(
                    "Cette action supprimera :",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Column([
                    ft.Text("• Tous les administrateurs", size=12),
                    ft.Text("• Tous les enseignants", size=12),
                    ft.Text("• Tous les élèves", size=12),
                    ft.Text("• Toutes les matières", size=12),
                    ft.Text("• Toutes les notes et bulletins", size=12),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.START,
                spacing=3
                ),
                ft.Text(
                    "⚠️ CETTE ACTION EST IRRÉVERSIBLE !",
                    color=ft.Colors.RED,
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    italic=True,
                    text_align=ft.TextAlign.CENTER
                )
            ],
            width=450,
            height=350,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10
            ),
            actions=[
                ft.TextButton(
                    "Annuler",
                    on_click=lambda e: Dialog.close_dialog(confirm_dialog)
                ),
                ft.ElevatedButton(
                    "Supprimer l'établissement",
                    bgcolor=ft.Colors.RED,
                    color=ft.Colors.WHITE,
                    icon=ft.Icons.DELETE_FOREVER,
                    on_click=lambda e: execute_delete_school(admin[7], confirm_dialog)
                )
            ]
        )
    
    def execute_delete_admin(admin, dialog):
        """Exécute la suppression d'un admin uniquement"""
        con = None
        try:
            con = get_db_connection()

            cur = con.cursor()
            
            cur.execute("DELETE FROM User WHERE identifiant = ? AND titre = 'admin'", (admin[1],))
            con.commit()
            
            Dialog.info_toast("Administrateur supprimé !")
            Dialog.close_dialog(dialog)
            Dialog.close_dialog(main_dialog)
            Stats(page, Donner)  # Rafraîchir
            
        except sqlite3.Error as e:
            Dialog.error_toast(f"Erreur de suppression: {str(e)}")
        finally:
            if con:
                con.close()
    
    def execute_delete_school(school_name, dialog):
        """Exécute la suppression de tout un établissement"""
        con = None
        try:
            con = get_db_connection()

            cur = con.cursor()
            
            # Supprimer tous les utilisateurs de l'établissement
            cur.execute("DELETE FROM User WHERE etablissement = ?", (school_name,))
            
            # Supprimer tous les élèves
            cur.execute("DELETE FROM Students WHERE etablissement = ?", (school_name,))
            
            # Supprimer toutes les matières
            cur.execute("DELETE FROM Matieres WHERE etablissement = ?", (school_name,))
            
            # Supprimer les enseignants de la table Teacher
            cur.execute("""
                DELETE FROM Teacher WHERE ident IN 
                (SELECT identifiant FROM User WHERE etablissement = ?)
            """, (school_name,))
            
            con.commit()
            
            Dialog.info_toast("Établissement supprimé avec toutes ses données !")
            Dialog.close_dialog(dialog)
            Dialog.close_dialog(main_dialog)
            Stats(page, Donner)  # Rafraîchir
            
        except sqlite3.Error as e:
            Dialog.error_toast(f"Erreur de suppression: {str(e)}")
        finally:
            if con:
                con.close()
    
    def create_admin_card(admin):
        """Crée une carte pour un administrateur"""
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, color=ft.Colors.RED, size=40),
                ft.Text(
                    f"{admin[3]} {admin[4]}",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(f"🏫 {admin[7]}", size=14, weight=ft.FontWeight.W_500),
                ft.Text(f"📧 {admin[5] or 'N/A'}", size=12),
                ft.Text(f"📞 {admin[6] or 'N/A'}", size=12),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.INFO,
                        tooltip="Détails",
                        icon_color=ft.Colors.BLUE,
                        on_click=lambda e, a=admin: show_admin_details(a)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Modifier",
                        icon_color=ft.Colors.GREEN,
                        on_click=lambda e, a=admin: edit_admin(a)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        tooltip="Supprimer l'admin",
                        icon_color=ft.Colors.ORANGE,
                        on_click=lambda e, a=admin: confirm_delete_admin(a)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_FOREVER,
                        tooltip="Supprimer l'établissement",
                        icon_color=ft.Colors.RED,
                        on_click=lambda e, a=admin: confirm_delete_school(a)
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5
            ),
            border=ft.border.all(2, ft.Colors.RED_200),
            border_radius=ft.border_radius.only(top_right=20, bottom_left=20),
            padding=15,
            margin=10,
            width=300,
            height=250,
        )
    
    # ==================== FONCTIONS POUR ADMIN (voir les profs) ====================
    def load_school_teachers():
        """Charge les enseignants de l'établissement de l'admin"""
        Etat = Return("etablissement")
        if not Etat:
            return []
        
        con = None
        try:
            con = get_db_connection()

            cur = con.cursor()
            cur.execute(
                "SELECT * FROM User WHERE etablissement = ? AND titre = 'prof'",
                (Etat[0][0],)
            )
            return cur.fetchall()
        except:
            return []
        finally:
            if con:
                con.close()
    
    def show_teacher_details(teacher):
        """Affiche les détails d'un enseignant"""
        # Récupérer la matière du prof
        prof_subject = "N/A"
        con = None
        try:
            con = get_db_connection()

            cur = con.cursor()
            cur.execute("SELECT matiere FROM Teacher WHERE ident = ?", (teacher[1],))
            result = cur.fetchone()
            if result:
                prof_subject = result[0]
        except:
            pass
        finally:
            if con:
                con.close()
        
        detail_dialog = Dialog.custom_dialog(
            title=f"📋 Détails Prof - {teacher[3]} {teacher[4]}",
            content=ft.Column([
                ft.Divider(),
                create_info_row("Nom:", teacher[3]),
                create_info_row("Prénom:", teacher[4]),
                create_info_row("Identifiant:", teacher[1]),
                create_info_row("Mot de passe:", teacher[2]),
                create_info_row("Email:", teacher[5]),
                create_info_row("Téléphone:", teacher[6]),
                create_info_row("Matière:", prof_subject),
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
    
    def edit_teacher(teacher):
        """Modifie un enseignant"""
        name_field = ft.TextField(label="Nom", value=teacher[3])
        prenom_field = ft.TextField(label="Prénom", value=teacher[4])
        ident_field = ft.TextField(label="Identifiant", value=teacher[1], read_only=True, disabled=True)
        pass_field = ft.TextField(label="Mot de passe", value=teacher[2])
        email_field = ft.TextField(label="Email", value=teacher[5])
        tele_field = ft.TextField(label="Téléphone", value=teacher[6])
        etabl_field = ft.TextField(label="Établissement", value=teacher[7], read_only=True, disabled=True)
        
        def save_changes(e, dialog):
            con = None
            try:
                con = get_db_connection()

                cur = con.cursor()
                
                cur.execute("""
                    UPDATE User 
                    SET nom = ?, passwords = ?, prenom = ?, email = ?, telephone = ?
                    WHERE identifiant = ? AND titre = 'prof'
                """, (
                    name_field.value.strip(),
                    pass_field.value,
                    prenom_field.value.strip(),
                    email_field.value.strip(),
                    tele_field.value.strip(),
                    ident_field.value
                ))
                con.commit()
                
                # NOUVEAU : Sync vers Supabase
                try:
                    from sync_manager import sync_manager
                    sync_manager.sync_table_to_supabase("User")
                except Exception as e:
                    Dialog.error_toast(f"⚠️ Erreur sync: {e}")
            
                Dialog.info_toast("Modifications enregistrées !")
                Dialog.close_dialog(dialog)
                Dialog.close_dialog(main_dialog)
                Stats(page, Donner)  # Rafraîchir
                
            except sqlite3.Error as e:
                Dialog.error_toast(f"Erreur: {str(e)}")
            finally:
                if con:
                    con.close()
        
        edit_dialog = Dialog.custom_dialog(
            title=f"✏️ Modifier - {teacher[3]} {teacher[4]}",
            content=ft.Column([
                name_field,
                prenom_field,
                ident_field,
                pass_field,
                email_field,
                tele_field,
                etabl_field,
            ],
            width=400,
            height=380,
            scroll=ft.ScrollMode.AUTO,
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
    
    def confirm_delete_teacher(teacher):
        """Demande confirmation avant suppression d'un prof"""
        confirm_dialog = Dialog.custom_dialog(
            title="⚠️ Confirmation de suppression",
            content=ft.Column([
                ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.RED, size=50),
                ft.Text(
                    "Êtes-vous sûr de vouloir supprimer cet enseignant ?",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    f"Enseignant: {teacher[3]} {teacher[4]}",
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
                    on_click=lambda e: execute_delete_teacher(teacher, confirm_dialog)
                )
            ]
        )
    
    def execute_delete_teacher(teacher, dialog):
        """Exécute la suppression d'un enseignant"""
        con = None
        try:
            con = get_db_connection()

            cur = con.cursor()
            
            # Supprimer de User
            cur.execute("DELETE FROM User WHERE identifiant = ? AND titre = 'prof'", (teacher[1],))
            
            # Supprimer de Teacher
            cur.execute("DELETE FROM Teacher WHERE ident = ?", (teacher[1],))
            
            con.commit()
            
            Dialog.info_toast("Enseignant supprimé !")
            Dialog.close_dialog(dialog)
            Dialog.close_dialog(main_dialog)
            Stats(page, Donner)  # Rafraîchir
            
        except sqlite3.Error as e:
            Dialog.error_toast(f"Erreur de suppression: {str(e)}")
        finally:
            if con:
                con.close()
    
    def create_teacher_card(teacher):
        """Crée une carte pour un enseignant"""
        # Récupérer la matière du prof
        prof_subject = "N/A"
        con = None
        try:
            con = get_db_connection()

            cur = con.cursor()
            cur.execute("SELECT matiere FROM Teacher WHERE ident = ?", (teacher[1],))
            result = cur.fetchone()
            if result:
                prof_subject = result[0]
        except:
            pass
        finally:
            if con:
                con.close()
        
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.GREEN, size=40),
                ft.Text(
                    f"{teacher[3]} {teacher[4]}",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(f"📚 {prof_subject}", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.PURPLE),
                ft.Text(f"📧 {teacher[5] or 'N/A'}", size=12),
                ft.Text(f"📞 {teacher[6] or 'N/A'}", size=12),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.INFO,
                        tooltip="Détails",
                        icon_color=ft.Colors.BLUE,
                        on_click=lambda e, t=teacher: show_teacher_details(t)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Modifier",
                        icon_color=ft.Colors.GREEN,
                        on_click=lambda e, t=teacher: edit_teacher(t)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        tooltip="Supprimer",
                        icon_color=ft.Colors.RED,
                        on_click=lambda e, t=teacher: confirm_delete_teacher(t)
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5
            ),
            border=ft.border.all(2, ft.Colors.GREEN_200),
            border_radius=ft.border_radius.only(top_right=20, bottom_left=20),
            padding=15,
            margin=10,
            width=280,
            height=240,
        )
    
    # ==================== GÉNÉRATION DU CONTENU SELON LE RÔLE ====================
    
    if Donner.get("role") == "creator":
        # ========== VUE CREATOR : Liste des ADMINS ==========
        admins = load_all_admins()
        
        # Cartes des admins
        admin_cards = [create_admin_card(admin) for admin in admins]
        
        if not admin_cards:
            admin_cards = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, size=60, color=ft.Colors.GREY_400),
                        ft.Text(
                            "Aucun administrateur",
                            size=16,
                            color=ft.Colors.GREY_600
                        ),
                        ft.Text(
                            "Ajoutez des administrateurs pour commencer",
                           
                            color=ft.Colors.GREY_500
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                    ),
                    padding=30
                )
            ]
        
        content = ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, color=ft.Colors.RED, size=30),
                    ft.Text(
                        f"Total: {len(admins)} administrateur(s)",
                        size=18,
                        weight=ft.FontWeight.BOLD
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10
                ),
                padding=10,
                bgcolor=ft.Colors.RED_50,
                border_radius=10,
            ),
            ft.Divider(),
            ft.Column(
                controls=admin_cards,
                scroll=ft.ScrollMode.AUTO,
                height=380,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
        main_dialog = Dialog.custom_dialog(
            title=f"📊 Statistiques - Liste des Administrateurs",
            content=ft.Container(
                content=content,
                width=500,
                height=500,
            ),
            actions=[
                ft.TextButton(
                    "Fermer",
                    icon=ft.Icons.CLOSE,
                    on_click=lambda e: Dialog.close_dialog(main_dialog)
                )
            ]
        )
    
    elif Donner.get("role") == "admin":
        # ========== VUE ADMIN : Liste des PROFS de son établissement ==========
        teachers = load_school_teachers()
        etablissement = Return("etablissement")
        etabl_name = etablissement[0][0] if etablissement else "N/A"
        
        # Cartes des enseignants
        teacher_cards = [create_teacher_card(teacher) for teacher in teachers]
        
        if not teacher_cards:
            teacher_cards = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SCHOOL, size=60, color=ft.Colors.GREY_400),
                        ft.Text(
                            "Aucun enseignant",
                            size=16,
                            color=ft.Colors.GREY_600
                        ),
                        ft.Text(
                            "Ajoutez des enseignants depuis le menu Gestion Enseignants",
                            size=12,
                            color=ft.Colors.GREY_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                    ),
                    padding=30
                )
            ]
        
        content = ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.BLUE, size=30),
                        ft.Text(
                            etabl_name,
                            size=18,
                            weight=ft.FontWeight.BOLD
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10
                    ),
                    ft.Row([
                        ft.Icon(ft.Icons.PERSON, color=ft.Colors.GREEN, size=25),
                        ft.Text(
                            f"Total: {len(teachers)} enseignant(s)",
                            size=16,
                            weight=ft.FontWeight.W_500
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10
                    ),
                ],
                spacing=5
                ),
                padding=15,
                bgcolor=ft.Colors.GREEN_50,
                border_radius=10,
            ),
            ft.Divider(),
            ft.Column(
                controls=teacher_cards,
                scroll=ft.ScrollMode.AUTO,
                height=360,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
        main_dialog = Dialog.custom_dialog(
            title=f"📊 Statistiques - Liste des Enseignants",
            content=ft.Container( 
                content=content,
                width=500,
                height=500,
            ),
            actions=[
                ft.TextButton(
                    "Fermer",
                    icon=ft.Icons.CLOSE,
                    on_click=lambda e: Dialog.close_dialog(main_dialog)
                )
            ]
        )
