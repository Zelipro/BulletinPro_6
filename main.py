import flet as ft
from Zeli_Dialog import ZeliDialog2
import sqlite3
import os
import shutil
from pathlib import Path
from time import sleep

#-------
from stats import Stats
from Students import Gestion_Eleve_Liste
from Note import Saisie_Notes
#from Bulletin import Generation_Bulletin
from sync_manager import sync_manager
from db_manager import get_db_connection, db_manager, init_all_tables
#-----


#======================= Pour Page 0 =======
#======================             ==============

def Get_on_db_local(mention):
    def User():
        donne = []
        con = None
        try:
            con = db_manager.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM User")
            donne = cur.fetchall()
            cur.close()
            
        except sqlite3.Error as e:
            pass
        finally:
            if con:
                con.close()
        return donne
    
    dic = {
        "User":User
    }
    
    func = dic.get(mention)
    if not func:
        return []   # return empty list when unknown mention
    return func()

def Submit(page , Ident , Pass): 
    Dialog = ZeliDialog2(page)
    #================================================================
    # NOUVEAU : Sync des Users au chargement de la page de login
    if not hasattr(Submit, 'users_synced'):
        loading = Dialog.loading_dialog(
            title="Chargement...",
            message="Synchronisation des utilisateurs"
        )
        
        # Initialiser tables locales
        sync_manager.init_local_tables()
        
        # Charger tous les users
        sync_manager.sync_on_login(
            callback=lambda msg: print(msg)
        )
        
        Dialog.close_dialog(loading)
        Submit.users_synced = True
    
    def login_success(donner_info,Dial):
        Dialog.close_dialog(Dial)
        
        # NOUVEAU : Charger les données de l'établissement
        
        if donner_info["role"] == "admin":
            Dialog.alert_dialog(
                title="Impossible",
                message="Veuillez utiliser BulletinPro version administrateur"
            )
            
            return # Ne pas continuer la connexion
        elif donner_info.get("role") != "creator":
            loading = Dialog.loading_dialog(
                title="Chargement...",
                message="Synchronisation des données de votre établissement"
            )
            
            # Récupérer l'établissement
            conn = sync_manager.get_local_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT etablissement FROM User WHERE identifiant = ? AND titre = ?",
                (donner_info["ident"], donner_info["role"])
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                etablissement = result[0]
                
                # Charger données établissement
                sync_manager.sync_etablissement_data(
                    etablissement,
                    callback=lambda msg: print(msg)
                )
                
                # Démarrer sync auto
                sync_manager.start_auto_sync(etablissement)
            
            Dialog.close_dialog(loading)
        
        # Afficher la page principale
        page.clean()
        sidebar, main_content = Page1(page, donner_info)
        page.add(ft.Row([sidebar, main_content], spacing=0, expand=True))
        page.update()
    
    # Reste du code inchangé...
    Donne = Get_on_db_local("User")
    if all([Ident.value == "Deg" , Pass.value == "Deg"]):
        Donner = {
                "ident": "Deg",
                "pass" : "Deg",
                "name": "Zeli",
                "role": "creator"
        }
        Dial = Dialog.custom_dialog(
            title = "Notification",
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE_OUTLINE,
                        size = 60,
                        color=ft.Colors.GREEN_200,
                    ),
                    ft.Text(
                        value="Bienvenue Mon createur"
                    )
                ],
                height=100,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions=[
                ft.ElevatedButton(
                    content=ft.Text(
                        value ="Ok",
                        color=ft.Colors.WHITE,
                        ),
                    bgcolor=ft.Colors.GREEN_300,
                    on_click=lambda e : login_success(Donner ,Dial )
                )
            ]
        )
        #pass #Nxte page
    elif Donne:
        found = False
        for elmt in Donne:
            ident , passs = elmt[1],elmt[2]
            if ident == Ident.value and passs == Pass.value:
                found = True
                
                Donner = {
                    "ident": ident,
                    "pass" : passs,
                    "name": elmt[3],
                    "role": elmt[8]
                    }
                
                Dial = Dialog.custom_dialog(
                    title = "Notification",
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE_OUTLINE,
                                size = 60,
                                color=ft.Colors.GREEN_200,
                            ),
                            ft.Text(
                                value=f"Bienvenue {Ident.value}"
                            )
                        ],
                        height=100,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    actions=[
                        ft.ElevatedButton(
                            content=ft.Text(
                                value ="Ok",
                                color=ft.Colors.WHITE,
                                ),
                            bgcolor=ft.Colors.GREEN_200,
                            on_click=lambda e : login_success(Donner ,Dial )
                        )
                    ]
                )
                #break  # stop after first match
        if not found:
            # show error dialog when no matching credentials found
            Dial = Dialog.custom_dialog(
                title = "Notification",
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.ERROR_ROUNDED,
                            size = 60,
                            color=ft.Colors.RED_200,
                        ),
                        ft.Text(
                            value="Erreur de connexion"
                        )
                    ],
                    height=100,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                actions=[
                    ft.ElevatedButton(
                        content=ft.Text(
                            value ="Ok",
                            color=ft.Colors.WHITE,
                            ),
                        bgcolor=ft.Colors.RED_200,
                        on_click=lambda e : Dialog.close_dialog(Dial)
                    )
                ]
            )
    else:
        Dial = Dialog.custom_dialog(
            title = "Notification",
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.ERROR_ROUNDED,
                        size = 60,
                        color=ft.Colors.RED_200,
                    ),
                    ft.Text(
                        value="Erreur de connexion"
                    )
                ],
                height=100,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions=[
                ft.ElevatedButton(
                    content=ft.Text(
                        value ="Ok",
                        color=ft.Colors.WHITE,
                        ),
                    bgcolor=ft.Colors.RED_200,
                    on_click=lambda e : Dialog.close_dialog(Dial)
                )
            ]
        )
def Page0(page):#page: ft.Page):
    page.title = "Login page"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    #page.bgcolor = "#1a0d2e"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    # Fonction de connexion
    def learn_more_click(e):
        page.snack_bar = ft.SnackBar(
            content=ft.Text("Learn More clicked!", color=ft.Colors.WHITE),
            bgcolor=ft.Colors.BLUE_700,
        )
        page.snack_bar.open = True
        page.update()
    
    # Champs de formulaire
    
    # Panneau gauche - Welcome
    left_panel = ft.Container(
        content=ft.Column([
            # Logo
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text("", size=0),
                        width=8,
                        height=30,
                        bgcolor=ft.Colors.WHITE,
                        border_radius=2,
                    ),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("", size=0),
                        width=8,
                        height=30,
                        bgcolor=ft.Colors.WHITE,
                        border_radius=2,
                    ),
                ], spacing=0),
                margin=ft.margin.only(bottom=40),
            ),
            
            # Welcome text
            ft.Text(
                "Welcome",
                size=60,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
            ),
            
            ft.Text(
                "On BulletinPro !",
                size=25,
                #weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
            ),
            
            # Ligne d�corative
            ft.Container(
                width=80,
                height=4,
                bgcolor="#ff6b6b",
                border_radius=2,
                margin=ft.margin.only(top=10, bottom=30),
            ),
            
            # Description
            ft.Container(
                content=ft.Text(
                    value = "Simplifiez la gestion académique de votre établissement.Générez des bulletins scolaires professionnels en quelques clics, suivez les performances de vos élèves et concentrez-vous sur l'essentiel : leur réussite éducative.Commencez dès maintenant et transformez votre gestion scolaire !",

                    size=14,
                    color="#b8a7d1",
                    text_align=ft.TextAlign.LEFT,
                ),
                width=350,
                margin=ft.margin.only(bottom=40),
            ),
            
            # Bouton Learn More
        ], 
        horizontal_alignment=ft.CrossAxisAlignment.START,
        spacing=0),
        padding=60,
        alignment=ft.alignment.center_left,
    )
    
    # Ajout d'une fonction pour gérer la visibilité du mot de passe
    def toggle_password_visibility(e):
        Pass.password = not Pass.password
        e.control.icon = ft.Icons.VISIBILITY_OFF if Pass.password else ft.Icons.VISIBILITY
        page.update()
    
    Pass = ft.TextField(
        label="Password",
        hint_text="Password",
        password=True,
        color=ft.Colors.WHITE,
        suffix_icon=ft.IconButton(
            icon=ft.Icons.VISIBILITY_OFF,
            icon_color=ft.Colors.WHITE60,
            on_click=toggle_password_visibility,
            tooltip="Afficher/Masquer le mot de passe"
        ),
    )
    Ident = ft.TextField(
        label =  "User Name",
        hint_text =  "User Name",
        color=ft.Colors.WHITE,
    )
    
    def forgot_password(e):
        Dialog = ZeliDialog2(page)
        
        def validate_and_search(e):
            if not all([name_field.value, surname_field.value, email_field.value]):
                error_text.value = "Tous les champs sont obligatoires"
                page.update()
                return
                
            Donne = Get_on_db_local("User")
            found = False
            
            for user in Donne:
                # Structure: id(0), ident(1), pass(2), nom(3), prenom(4), annee(5), email(6)
                if all([user[3].lower() == name_field.value.lower(),
                       user[4].lower() == surname_field.value.lower(),
                       user[6].lower() == email_field.value.lower()]):
                    found = True
                    if user[8]: # Si c'est un mot de passe par défaut
                        Dialog.custom_dialog(
                            title="Récupération réussie",
                            content=ft.Column(
                                [
                                    ft.Icon(
                                        ft.Icons.CHECK_CIRCLE_OUTLINE,
                                        size=50,
                                        color=ft.Colors.GREEN
                                    ),
                                    ft.Text("Vos identifiants:"),
                                    ft.Container(height=10),
                                    ft.Text(f"Identifiant: {user[1]}", size=16),
                                    ft.Text(f"Mot de passe: {user[2]}", size=16, weight=ft.FontWeight.BOLD),
                                ],
                                height=200,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            actions=[
                                ft.ElevatedButton(
                                    text="Ok",
                                    bgcolor=ft.Colors.GREEN,
                                    color=ft.Colors.WHITE,
                                    on_click=lambda e: Dialog.close_dialog(search_dialog)
                                )
                            ]
                        )
                    else:
                        Dialog.alert_dialog(
                            title="Mot de passe personnalisé",
                            message="Vous avez personnalisé votre mot de passe. Veuillez répondre à votre question de sécurité."
                        )
                        security_dialog = Dialog.custom_dialog(
                            title="Question de sécurité",
                            content=ft.Column(
                                [
                                    ft.Text("Question:"),
                                    ft.Text(user[9], size=16, weight=ft.FontWeight.BOLD),  # question
                                    ft.Container(height=20),
                                    ft.TextField(
                                        label="Votre réponse",
                                        password=True
                                    ),
                                    ft.Text("", color="red")  # error text
                                ],
                                height=200,
                                width=400,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            actions=[
                                ft.TextButton("Annuler", 
                                            on_click=lambda e: Dialog.close_dialog(security_dialog)),
                                ft.ElevatedButton(
                                    "Vérifier",
                                    on_click=lambda e: verify_security_answer(
                                        security_dialog.content.controls[3].value,  # réponse
                                        user[10],  # réponse correcte
                                        security_dialog,
                                        user,
                                        security_dialog.content.controls[4]  # error text
                                    )
                                )
                            ]
                        )
                    break
                    
            if not found:
                error_text.value = "Aucun compte trouvé avec ces informations"
                page.update()

        def verify_security_answer(answer, correct_answer, dialog, user, error_text):
            if answer == correct_answer:
                Dialog.custom_dialog(
                    title="Identifiants récupérés",
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.LOCK_OPEN, color=ft.Colors.GREEN, size=50),
                            ft.Text("Vos identifiants:"),
                            ft.Text(f"Identifiant: {user[1]}", size=16),
                            ft.Text(f"Mot de passe: {user[2]}", size=16, weight=ft.FontWeight.BOLD)
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    actions=[
                        ft.ElevatedButton("Ok", 
                                        on_click=lambda e: [Dialog.close_dialog(dialog), 
                                                          Dialog.close_dialog(search_dialog)])
                    ]
                )
            else:
                error_text.value = "Réponse incorrecte"
                page.update()

        name_field = ft.TextField(
            label="Nom",
            hint_text="Votre nom",
            width=300,
            text_align=ft.TextAlign.CENTER,
        )
        
        surname_field = ft.TextField(
            label="Prénom",
            hint_text="Votre prénom",
            width=300,
            text_align=ft.TextAlign.CENTER,
        )
        
        email_field = ft.TextField(
            label="Email",
            hint_text="Votre email",
            width=300,
            text_align=ft.TextAlign.CENTER,
        )
        
        error_text = ft.Text(
            value="",
            color=ft.Colors.RED,
            size=12,
        )

        search_dialog = Dialog.custom_dialog(
            title="Récupération de mot de passe",
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.PASSWORD_ROUNDED,
                        size=50,
                        color=ft.Colors.BLUE,
                    ),
                    ft.Container(height=10),
                    ft.Text(
                        "Veuillez entrer vos informations",
                        text_align=ft.TextAlign.CENTER,
                        size=14,
                    ),
                    ft.Container(height=20),
                    name_field,
                    surname_field,
                    email_field,
                    error_text,
                ],
                height=400,
                width=400,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
            ),
            actions=[
                ft.TextButton(
                    text="Annuler",
                    on_click=lambda e: Dialog.close_dialog(search_dialog)
                ),
                ft.ElevatedButton(
                    text="Rechercher",
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    on_click=validate_and_search
                ),
            ]
        )

    # Panneau droit - Sign in
    right_panel = ft.Container(
        content=ft.Column([
            # Titre Sign in
            ft.Text(
                "Sign in",
                size=36,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
                text_align=ft.TextAlign.CENTER,
            ),
            
            ft.Container(height=30),
            
            # User Name
            ft.Column([
                Ident,
                ft.Container(height=8),
            ], spacing=0),
            
            ft.Container(height=20),
            
            # Password
            ft.Column([
                Pass,
                ft.Container(height=8),
            ], spacing=0),
            
            ft.Container(height=5),
            
            # Lien "Mot de passe oublié"
            ft.TextButton(
                text = "Mot de passe oublié",
                on_click=forgot_password,
                ),
            ft.Container(height=30),
            ft.Container(
                content=ft.Text(
                    "Submit",
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.WHITE,
                    text_align=ft.TextAlign.CENTER,
                ),
                width=280,
                height=50,
                bgcolor=None,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.center_left,
                    end=ft.alignment.center_right,
                    colors=["#ff7b54", "#ff5252"],
                ),
                border_radius=25,
                alignment=ft.alignment.center,
                ink=True,
                on_click = lambda e : Submit(page , Ident , Pass),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=20,
                    color="#ff5252",
                    offset=ft.Offset(0, 5),
                ),
            ),
            
            ft.Container(height=25),
            
            # Social media Icons
            ft.Row([
                ft.IconButton(
                    icon=ft.Icons.FACEBOOK,
                    icon_color=ft.Colors.WHITE,
                    icon_size=22,
                    tooltip="Facebook",
                ),
                ft.IconButton(
                    icon=ft.Icons.CAMERA_ALT,
                    icon_color=ft.Colors.WHITE,
                    icon_size=22,
                    tooltip="Instagram",
                ),
                ft.IconButton(
                    icon=ft.Icons.PUSH_PIN,
                    icon_color=ft.Colors.WHITE,
                    icon_size=22,
                    tooltip="Pinterest",
                ),
            ], 
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=15),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=0),
        bgcolor="#3d2f52",
        padding=50,
        border_radius=ft.border_radius.only(top_right=15, bottom_right=15),
        width=400,
        #alignment=ft.alignment.center,
    )
    
    # Conteneur principal avec fond d�coratif
    main_container = ft.Container(
        content=ft.Stack([
            # Formes d�coratives en arri�re-plan
            ft.Container(
                width=400,
                height=400,
                border_radius=200,
                bgcolor="#2d1b47",
                opacity=0.3,
                left=-100,
                top=-100,
            ),
            ft.Container(
                width=300,
                height=300,
                border_radius=150,
                bgcolor="#4a2d6b",
                opacity=0.2,
                right=-50,
                top=100,
            ),
            ft.Container(
                width=200,
                height=200,
                border_radius=100,
                bgcolor="#5c3d7a",
                opacity=0.25,
                left=100,
                bottom=-50,
            ),
            
            # Panneau de login avec effet glassmorphism
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=left_panel,
                        bgcolor="#2d1947",
                        expand=True,
                        border_radius=ft.border_radius.only(top_left=15, bottom_left=15),
                    ),
                    right_panel,
                ], spacing=0),
                width=900,
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=50,
                    color="#000000",
                    offset=ft.Offset(0, 10),
                ),
                border_radius=15,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ),
        ]),
        alignment=ft.alignment.center,
        expand=True,
    )
    
    # Boutons en haut
    
    # Layout complet
    return ft.Stack([
            main_container,
        ], expand=True)



#==============================================================================
def get_user_preference(setting_name,Donner):
    """Récupère les préférences utilisateur"""
    con = None
    try:
        con = db_manager.get_connection()
        cur = con.cursor()
        
        if Donner and Donner.get("ident") == "Deg":
            cur.execute(f"SELECT {setting_name} FROM Dev_Preferences WHERE id = 1")
        else:
            cur.execute(f"SELECT {setting_name} FROM User_Preferences WHERE user_id = ?",
                       (Donner.get("ident") if Donner else None,))
        
        result = cur.fetchone()
        return result[0] if result else "light" if setting_name == "theme" else "fr"
    except sqlite3.Error:
        return "light" if setting_name == "theme" else "fr"
    finally:
        if con:
            con.close()

def User_Config(page, Donner):  # Ajout du paramètre Donner
    """Gestion des préférences utilisateur (mode/langue)
    Maintenant: applique automatiquement les préférences stockées au chargement.
    """
    Dialog = ZeliDialog2(page)

    # --- apply stored preferences immediately on load ---
    try:
        pref_theme = get_user_preference("theme", Donner)
        pref_lang = get_user_preference("language", Donner)
        page.theme_mode = ft.ThemeMode.DARK if pref_theme == "dark" else ft.ThemeMode.LIGHT
        # you can store language on page or Info if needed
        page.update()
    except Exception:
        pass
    
    def save_preferences(theme, language, dialog):
        con = None
        try:
            con = db_manager.get_connection()
            cur = con.cursor()
            
            # Table pour développeur
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Dev_Preferences (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    theme TEXT DEFAULT 'light',
                    language TEXT DEFAULT 'fr'
                )
            """)
            
            # Table pour utilisateurs normaux
            cur.execute("""
                CREATE TABLE IF NOT EXISTS User_Preferences (
                    user_id TEXT PRIMARY KEY,
                    theme TEXT DEFAULT 'light',
                    language TEXT DEFAULT 'fr'
                )
            """)
            
            if Donner and Donner.get("ident") == "Deg":  # Utilisation de Donner
                cur.execute("""
                    INSERT OR REPLACE INTO Dev_Preferences (id, theme, language)
                    VALUES (1, ?, ?)
                """, (theme, language))
            elif Donner:  # Vérification que Donner existe
                cur.execute("""
                    INSERT OR REPLACE INTO User_Preferences (user_id, theme, language)
                    VALUES (?, ?, ?)
                """, (Donner.get("ident"), theme, language))
            
            con.commit()
            
            # Appliquer le thème immédiatement
            page.theme_mode = ft.ThemeMode.DARK if theme == "dark" else ft.ThemeMode.LIGHT
            page.update()
            
            Dialog.alert_dialog(title="Succès", message="Préférences enregistrées!")
            Dialog.close_dialog(dialog)
            
        except sqlite3.Error as e:
            Dialog.alert_dialog(title="Erreur", message=str(e))
        finally:
            if con:
                con.close()
    
    config_dialog = Dialog.custom_dialog(
        title="Préférences",
        content=ft.Column([
            ft.Switch(
                label="Mode sombre",
                value=get_user_preference("theme",Donner) == "dark"
            ),
            ft.Container(height=3),
            ft.Dropdown(
                label="Langue",
                options=[
                    ft.dropdown.Option("fr", "Français"),
                    ft.dropdown.Option("en", "English")
                ],
                value=get_user_preference("language",Donner)
            )
        ], width=300, height=200),
        actions=[
            ft.TextButton("Annuler", on_click=lambda e : Dialog.close_dialog(config_dialog)),
            ft.ElevatedButton(
                "Enregistrer",
                on_click=lambda e: save_preferences(
                    "dark" if config_dialog.content.controls[0].value else "light",
                    config_dialog.content.controls[2].value,
                    config_dialog
                )
            )
        ]
    )

def New_admin(page,Donner):
    Dialog = ZeliDialog2(page)
    
    def Verif_ident_in(Ident , passs):
        con = None
        try:
            con = db_manager.get_connection()
            cur = con.cursor()
            
            # Créer la table School
            cur.execute("""
                CREATE TABLE IF NOT EXISTS User (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifiant TEXT NOT NULL,
                    passwords TEXT NOT NULL,
                    nom TEXT NOT NULL,
                    prenom TEXT NOT NULL,
                    email TEXT NOT NULL,
                    telephone TEXT NOT NULL,
                    etablissement TEXT NOT NULL,
                    titre TEXT NOT NULL,
                    theme TEXT DEFAULT 'light',
                    language TEXT DEFAULT 'fr'
                )
            """)
            con.commit()
            cur.close()
            
            cur = con.cursor()
            # Insérer l'admin
            cur.execute("SELECT * FROM User WHERE identifiant = ? AND passwords = ?",(Ident , passs))
            donner = cur.fetchall()
            
            con.commit()
            cur.close()
            
            return not donner == []
        except:
            return False
        
    def save_admin(fields, dialog):
        con = None
        try:
            con = db_manager.get_connection()
            cur = con.cursor()
            # Insérer l'admin
            cur.execute("INSERT INTO User (identifiant, passwords, nom, prenom, email, telephone,  etablissement , titre)  VALUES (?, ?, ?, ?, ?, ?, ?, 'admin')",tuple(fields))

            con.commit()
            cur.close()
            
            dialg2 = Dialog.custom_dialog(
                title="",
                content=ft.Column(
                    [
                        ft.Icon(
                           ft.Icons.CHECK_CIRCLE,
                           size = 60,
                           color = ft.Colors.GREEN
                        ),
                        ft.Container(height=2),
                        ft.Text(
                            value = "Succès",
                            weight=ft.FontWeight.BOLD,
                            size = 30,
                            color=ft.Colors.GREEN
                        ),
                        ft.Text(
                            value = f"""admin créé avec succès!
                                \nIdentifiant: {fields[0]}
                                \nMot de passe: {fields[1]}"""
                        )
                    ],
                    height=250,
                    width=400,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                actions=[
                    ft.ElevatedButton(
                        text = "Ok",
                        width=100,
                        bgcolor=ft.Colors.GREEN,
                        color=ft.Colors.WHITE,
                        on_click=lambda e : Dialog.close_dialog(dialg2)
                    )
                ]
            )
            Dialog.close_dialog(dialog)
            
        except sqlite3.Error as e:
            Dialog.alert_dialog(title="Erreur", message=str(e))
        finally:
            if con:
                con.close()
        
    fields = [
        ft.TextField(label="Nom admin",text_align="center"),
        ft.TextField(label="Prénom admin",text_align="center"),
        ft.TextField(label="Email admin",text_align="center"),
        ft.TextField(label="Téléphone admin",text_align="center"),
        ft.TextField(label="Nom École",text_align="center"),
    ]
    
    def valider(e, dialog, fields):
        error = False
        for field in fields:
            if not field.value:
                field.error_text = "Champ requis"
                error = True
        
        if error:
            page.update()
            return
        else:
            Name = fields[0].value
            Prenom = fields[1].value
            Ident = f"{Prenom[0]}{Name}".upper()
            Pass = f"{Prenom.lower()}@admin_{len(Name)+len(Prenom)}"

            Result = Verif_ident_in(Ident,Pass)
            if not Result:
                save_admin([Ident,Pass] + [elmt.value for elmt in fields], dialog)
            else:
                fields[0].error_text = "Cet Nom et Prenom existe déjà"
                fields[1].error_text = "Cet Nom et Prenom existe déjà"
                page.update()
        
    dialog = Dialog.custom_dialog(
        title="Nouvel administrateur",
        content=ft.Column([
            ft.Text("Ajouter un administrateur", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            *fields,
        ], width=400, height=400, scroll=ft.ScrollMode.AUTO),
        actions=[
            ft.TextButton("Annuler", on_click=lambda e: Dialog.close_dialog(dialog)),
            ft.ElevatedButton(
                "Valider",
                bgcolor=ft.Colors.BLUE,
                color=ft.Colors.WHITE,
                on_click=lambda e: valider(e, dialog, fields)
            )
        ]
    )

def Setting(page, Donner=None):
    Dialog = ZeliDialog2(page)
    
    # Définir les informations par défaut pour le créateur
    if not Donner:
        Donner = {
            "ident": "Deg",
            "role": "creator",
            "pass": None,
            "name": "Développeur"
        }
    
    def Return(Ident):
        """Récupère une information depuis la table User"""
        con = None
        try:
            con = db_manager.get_connection()
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
    
    def save_settings(fields_dict, dial, theme_value, lang_value):
        """Enregistre les paramètres selon le type d'utilisateur"""
        con = None
        try:
            con = db_manager.get_connection()
            cur = con.cursor()
            
            # Déterminer le thème
            theme = "dark" if theme_value else "light"
            
            if Donner.get("role") == "creator":
                # Créer la table Dev_Preferences si elle n'existe pas
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS Dev_Preferences (
                        id INTEGER PRIMARY KEY DEFAULT 1,
                        theme TEXT DEFAULT 'light',
                        language TEXT DEFAULT 'fr'
                    )
                """)
                con.commit()
                
                # Enregistrer pour le développeur
                cur.execute("""
                    INSERT OR REPLACE INTO Dev_Preferences (id, theme, language)
                    VALUES (1, ?, ?)
                """, (theme, lang_value))
                
            else:
                # Pour admin et prof
                # Récupérer les données actuelles
                cur.execute(
                    "SELECT * FROM User WHERE identifiant = ? AND titre = ? AND passwords = ?",
                    (Donner.get("ident"), Donner.get("role"), Donner.get("pass"))
                )
                current_data = cur.fetchone()
                
                if not current_data:
                    Dialog.error_toast("Utilisateur non trouvé")
                    return
                
                # Mettre à jour les informations
                cur.execute("""
                    UPDATE User 
                    SET passwords = ?,
                        nom = ?,
                        prenom = ?,
                        email = ?,
                        telephone = ?,
                        etablissement = ?,
                        theme = ?,
                        language = ?
                    WHERE identifiant = ? AND titre = ?
                """, (
                    fields_dict["password"].value,
                    fields_dict["nom"].value,
                    fields_dict["prenom"].value,
                    fields_dict["email"].value,
                    fields_dict["telephone"].value,
                    fields_dict["etablissement"].value,
                    theme,
                    lang_value,
                    Donner.get("ident"),
                    Donner.get("role")
                ))
            
            con.commit()
            
            # Appliquer le thème immédiatement
            page.theme_mode = ft.ThemeMode.DARK if theme == "dark" else ft.ThemeMode.LIGHT
            page.update()
            
            Dialog.alert_dialog(
                title="Succès",
                message="Paramètres enregistrés avec succès!"
            )
            
            Dialog.close_dialog(dial)
            
        except sqlite3.Error as e:
            Dialog.alert_dialog(
                title="Erreur",
                message=f"Erreur lors de l'enregistrement: {str(e)}"
            )
        finally:
            if con:
                con.close()
    
    def toggle_password_visibility(e, password_field, icon_button):
        """Basculer la visibilité du mot de passe"""
        password_field.password = not password_field.password
        icon_button.icon = ft.Icons.VISIBILITY_OFF if password_field.password else ft.Icons.VISIBILITY
        page.update()
    
    def enable_password_edit(e, password_field):
        """Activer l'édition du mot de passe"""
        password_field.read_only = False
        password_field.border_color = ft.Colors.BLUE
        page.update()
    
    # Récupérer les préférences actuelles
    current_theme = get_user_preference("theme", Donner)
    current_lang = get_user_preference("language", Donner)
    
    # Créer l'onglet Système (commun à tous)
    theme_switch = ft.Switch(
        label="Mode sombre",
        value=current_theme == "dark",
        on_change=lambda e: page.update(),
    )
    
    lang_dropdown = ft.Dropdown(
        label="Langue",
        value=current_lang,
        options=[
            ft.dropdown.Option("fr", "Français"),
            ft.dropdown.Option("en", "English")
        ],
        on_change=lambda e: page.update(),
    )
    
    system_tab = ft.Tab(
        text="Système",
        icon=ft.Icons.SETTINGS,
        content=ft.Container(
            content=ft.Column([
                ft.Text("Préférences du système", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                theme_switch,
                lang_dropdown,
            ], spacing=15),
            padding=20,
        )
    )
    
    # Liste des onglets
    tabs_list = [system_tab]
    fields_dict = {}
    
    # Ajouter l'onglet Profil seulement pour admin et prof
    if Donner.get("role") in ["admin", "prof"]:
        # Champs pour le profil
        ident_field = ft.TextField(
            label="Identifiant",
            value=Donner.get("ident"),
            read_only=True,
            disabled=True,
            text_align="center"
        )
        
        # Récupérer les données utilisateur
        user_data = None
        con = None
        try:
            con = db_manager.get_connection()
            cur = con.cursor()
            cur.execute(
                "SELECT * FROM User WHERE identifiant = ? AND titre = ? AND passwords = ?",
                (Donner.get("ident"), Donner.get("role"), Donner.get("pass"))
            )
            user_data = cur.fetchone()
        except:
            pass
        finally:
            if con:
                con.close()
        
        # Boutons pour le mot de passe
        visibility_button = ft.IconButton(
            icon=ft.Icons.VISIBILITY_OFF,
            icon_color=ft.Colors.GREY_600,
            tooltip="Afficher/Masquer"
        )
        
        password_field = ft.TextField(
            label="Mot de passe",
            value=user_data[2] if user_data else "",
            password=True,
            read_only=True,
            text_align="center",
            suffix=visibility_button,
            prefix=ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_color=ft.Colors.BLUE,
                tooltip="Modifier",
                on_click=lambda e: enable_password_edit(e, password_field)
            )
        )
        
        # Lier l'événement de visibilité
        visibility_button.on_click = lambda e: toggle_password_visibility(e, password_field, visibility_button)
        
        nom_field = ft.TextField(
            label="Nom",
            value=user_data[3] if user_data else "",
            text_align="center",
            capitalization=ft.TextCapitalization.WORDS
        )
        
        prenom_field = ft.TextField(
            label="Prénom",
            value=user_data[4] if user_data else "",
            text_align="center",
            capitalization=ft.TextCapitalization.WORDS
        )
        
        email_field = ft.TextField(
            label="Email",
            value=user_data[5] if user_data else "",
            text_align="center",
            keyboard_type=ft.KeyboardType.EMAIL
        )
        
        telephone_field = ft.TextField(
            label="Téléphone",
            value=user_data[6] if user_data else "",
            text_align="center",
            keyboard_type=ft.KeyboardType.PHONE
        )
        
        etablissement_field = ft.TextField(
            label="Établissement",
            value=user_data[7] if user_data else "",
            read_only=True,
            disabled=True,
            text_align="center"
        )
        
        # Stocker les champs dans le dictionnaire
        fields_dict = {
            "password": password_field,
            "nom": nom_field,
            "prenom": prenom_field,
            "email": email_field,
            "telephone": telephone_field,
            "etablissement": etablissement_field
        }
        
        # Créer l'onglet Profil
        profile_tab = ft.Tab(
            text="Profil",
            icon=ft.Icons.PERSON,
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Informations personnelles", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ident_field,
                    password_field,
                    nom_field,
                    prenom_field,
                    email_field,
                    telephone_field,
                    etablissement_field,
                ], spacing=15, scroll=ft.ScrollMode.AUTO),
                padding=20,
            )
        )
        
        tabs_list.insert(0, profile_tab)  # Insérer en premier
    
    # Créer le contenu avec onglets
    settings_content = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=tabs_list,
        expand=True,
    )
    
    # Créer le dialog
    dial = Dialog.custom_dialog(
        title=f"⚙️ Paramètres - {Donner.get('name', 'Utilisateur')}",
        content=ft.Container(
            content=settings_content,
            width=450,
            height=400,
        ),
        actions=[
            ft.TextButton(
                "Annuler",
                icon=ft.Icons.CLOSE,
                on_click=lambda e: Dialog.close_dialog(dial)
            ),
            ft.ElevatedButton(
                "Enregistrer",
                icon=ft.Icons.SAVE,
                bgcolor=ft.Colors.GREEN,
                color=ft.Colors.WHITE,
                on_click=lambda e: save_settings(
                    fields_dict,
                    dial,
                    theme_switch.value,
                    lang_dropdown.value
                )
            )
        ]
    )



#===== Gestion des eleves ============

#Dans la fonction studnets
    
#====================================

def get_authorized_items(role):
    if role == "creator":
        return [
            {"icon": ft.Icons.ADMIN_PANEL_SETTINGS, "text": "Gestion admin", "color": ft.Colors.RED,
             "desc": "Ajouter/Gérer les administrateurs", "route": "/admin", "fonct": New_admin},
            {"icon": ft.Icons.SETTINGS, "text": "Configuration", "color": ft.Colors.BROWN,
             "desc": "Paramètres système", "route": "/settings", "fonct": Setting},
            {"icon": ft.Icons.BAR_CHART, "text": "Statistiques", "color": ft.Colors.INDIGO,
             "desc": "Analyses et graphiques", "route": "/stats", "fonct": Stats},
        ]
    elif role == "admin":
        return None  #Pour les adimistraction j'ai fait specialement une version administracteur Bulletin.py
    else:  # Enseignant
        return [
            {"icon": ft.Icons.GRADE, "text": "Saisie Notes", "color": ft.Colors.RED,
             "desc": "Notes et moyennes", "route": "/grades", "fonct": Saisie_Notes},
            {"icon": ft.Icons.LIST, "text": "Liste Élèves", "color": ft.Colors.BLUE,
             "desc": "Consulter les élèves", "route": "/view_students", "fonct": Gestion_Eleve_Liste},
            {"icon": ft.Icons.SETTINGS, "text": "Paramètres", "color": ft.Colors.BROWN,
             "desc": "Configuration", "route": "/settings", "fonct": Setting},
        ]

def Page1(page, Donner = None):
    page.title = "Bulletin Pro"
    page.padding = 0
    #page.theme_mode = ft.ThemeMode.LIGHT
    
    def logOut():
        page.clean()
        page.add(Page0(page))
        page.update()
        
    if not Donner:
        Info = {
            "ident": "Deg",
            "name": "Zeli",
            "role": "creator"
        }
    else:
        Info = Donner
    User_Config(page, Info)
    # Get authorized menu items and cards based on role
    dashboard_cards = get_authorized_items(Info.get("role", "Teacher"))
    
    # Create menu items from dashboard cards
    menu_items = [{"icon": ft.Icons.HOME, "text": "Accueil", "route": "/"}]
    menu_items.extend([
        {"icon": card["icon"], "text": card["text"], "route": card["route"]}
        for card in dashboard_cards
    ])

    # Create card widgets
    cards = []
    for card in dashboard_cards:
        cards.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(card["icon"], color=card["color"], size=40),
                    ft.Text(card["text"], 
                            #color=ft.Colors.BLACK,
                           size=16, 
                           weight=ft.FontWeight.W_500,
                           text_align=ft.TextAlign.CENTER),
                    ft.Container(height=5),
                    ft.Text(card["desc"],
                           #color=ft.Colors.GREY_700,
                           size=12,
                           text_align=ft.TextAlign.CENTER),
                ], 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
                alignment=ft.MainAxisAlignment.CENTER),
                #bgcolor=ft.Colors.WHITE,
                width=200,
                height=180,
                border_radius=15,
                padding=20,
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                alignment=ft.alignment.center,
                on_click=lambda e, f=card["fonct"]: f(page,Donner),  # Appel de la fonction associée
                ink=True,
            )
        )

    # Main content with role indication
    main_content = ft.Container(
        #bgcolor = ft.Colors.DARK_BLUE,
        content=ft.Column([
            # Header
            ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text("Tableau de Bord", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"Bienvenue {Info.get('name', 'admin')} ({Info.get('role', 'Teacher')})", 
                            size=16, 
                            color=ft.Colors.GREY_700
                        ),
                    ]),
                    ft.Container(expand=True),
                    ft.CircleAvatar(
                        content=ft.Text(
                            (Donner['name'][0] if Donner else 'A').upper(),
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                        bgcolor=ft.Colors.BLUE,
                        radius=20,
                    ),
                ]),
                padding=20,
                #bgcolor=ft.Colors.WHITE,
            ),
            # Search bar
            ft.Container(
                content=ft.TextField(
                    hint_text="Search",
                    prefix_icon=ft.Icons.SEARCH,
                    border_color=ft.Colors.GREY_300,
                    filled=True,
                    #bgcolor=ft.Colors.WHITE,
                ),
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
            ),
            # Dashboard cards grid
            ft.Container(
                content=ft.GridView(
                    controls=cards,
                    runs_count=4,
                    max_extent=250,
                    child_aspect_ratio=1.1,
                    spacing=20,
                    run_spacing=20,
                    padding=20,
                ),
                expand=True,
            ),
        ]),
        #bgcolor="#f5f5f5",
        expand=True,
    )
    
    # Sidebar
    sidebar = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.WHITE),
                    ft.Text("SCHOOL", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                ]),
                padding=20,
                ink  = True,
                on_click= lambda e : logOut()
            ),
            ft.Divider(height=1, ),#color=ft.Colors.WHITE24),
            *[
                ft.Container(
                    content=ft.Row([
                        ft.Icon(item["icon"], color=ft.Colors.WHITE70, size=20),
                        ft.Text(item["text"], color=ft.Colors.WHITE70, size=14),
                    ]),
                    padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    on_click=lambda e, route=item["route"]: page.go(route),
                )
                for item in menu_items
            ],
        ]),
        width=250,
        bgcolor="#2c3e50",
        padding=ft.padding.only(top=10),
    )
    
    return sidebar,main_content

def get_school_setting(setting_name,Info):
    """Récupère un paramètre de l'école depuis la base de données"""
    con = None
    Ident = Info.get("ident")
    title = Info.get("role")
    table = "User"
    try:
        con = db_manager.get_connection()
        cur = con.cursor()
        cur.execute(f"SELECT {setting_name} FROM {table} WHERE identifiant = ? AND titre = ? ",(Ident , title))
        result = cur.fetchone()
        return result[0] if result else None
    except sqlite3.Error:
        return None
    finally:
        if con:
            con.close()

def update_language(lang_code):
    """Met à jour les traductions de l'interface"""
    # TODO: Implémenter le système de traduction
    pass

"""def main(page: ft.Page):
    # Layout
    Donner = {
            "ident": "EATIKPO",
            "pass" : "e@prof_12",
            "name": "ATIKPO",
            "role": "prof"
    }
    Main = Page1(page,Donner)
    page.add(
        ft.Row([
            Main[0],
            Main[1],
        ], spacing=0, expand=True)
    )

ft.app(target=main)"""

def main(page : ft.Page):
    from sync_manager import sync_manager
    sync_manager.init_local_tables()
    
    page.add(
        Page0(page)
    )
    
ft.app(target=main)