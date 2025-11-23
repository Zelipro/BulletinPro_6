import flet as ft
import time
from typing import Callable, Optional, List

class ZeliDialog2:
    """
    Système complet de dialogs et notifications pour Flet
    Équivalent de MDDialog, Toast, Snackbar de KivyMD
    """
    
    def __init__(self, page):
        self.page = page
        self.active_toasts = []
        self.toast_container = None
        self._init_toast_container()
    
    def _init_toast_container(self):
        """Initialise le conteneur pour les toasts"""
        self.toast_container = ft.Column(
            controls=[],
            spacing=10,
            right=20,
            bottom=20,
            alignment=ft.MainAxisAlignment.END,
        )
        if self.toast_container not in self.page.overlay:
            self.page.overlay.append(self.toast_container)
    
    # ==================== TOAST ====================
    def show_toast(
        self,
        message: str,
        duration: int = 3,
        bgcolor: str = "#323232",
        color: str = "#FFFFFF",
        icon: Optional[str] = None,
        position: str = "bottom",  # "bottom", "top", "center"
    ):
        """
        Affiche un toast (message temporaire)
        
        Args:
            message: Texte à afficher
            duration: Durée en secondes
            bgcolor: Couleur de fond
            color: Couleur du texte
            icon: Icône optionnelle
            position: Position du toast
        """
        # Créer le contenu du toast
        content_widgets = []
        
        if icon:
            content_widgets.append(
                ft.Icon(icon, size=20, color=color)
            )
        
        content_widgets.append(
            ft.Text(message, color=color, size=14, weight=ft.FontWeight.W_500)
        )
        
        toast = ft.Container(
            content=ft.Row(
                controls=content_widgets,
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor=bgcolor,
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            border_radius=8,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color="#00000040",
                offset=ft.Offset(0, 2),
            ),
            opacity=0,
            animate_opacity=ft.Animation(300, "easeOut"),
        )
        
        # Positionner selon la position demandée
        if position == "bottom":
            if self.toast_container not in self.page.overlay:
                self.page.overlay.append(self.toast_container)
            self.toast_container.controls.append(toast)
        elif position == "top":
            toast.top = 20
            toast.right = 20
            self.page.overlay.append(toast)
        else:  # center
            toast.top = self.page.height / 2 - 50
            toast.left = self.page.width / 2 - 150
            self.page.overlay.append(toast)
        
        self.page.update()
        
        # Animation d'entrée
        toast.opacity = 1
        self.page.update()
        
        # Fermeture automatique
        def close_toast():
            time.sleep(duration)
            toast.opacity = 0
            self.page.update()
            time.sleep(0.3)
            if toast in self.toast_container.controls:
                self.toast_container.controls.remove(toast)
            elif toast in self.page.overlay:
                self.page.overlay.remove(toast)
            self.page.update()
        
        import threading
        threading.Thread(target=close_toast, daemon=True).start()
    
    def success_toast(self, message: str, duration: int = 3):
        """Toast de succès (vert)"""
        self.show_toast(
            message,
            duration=duration,
            bgcolor="#4CAF50",
            icon=ft.Icons.CHECK_CIRCLE,
        )
    
    def error_toast(self, message: str, duration: int = 3):
        """Toast d'erreur (rouge)"""
        self.show_toast(
            message,
            duration=duration,
            bgcolor="#F44336",
            icon=ft.Icons.ERROR,
        )
    
    def warning_toast(self, message: str, duration: int = 3):
        """Toast d'avertissement (orange)"""
        self.show_toast(
            message,
            duration=duration,
            bgcolor="#FF9800",
            icon=ft.Icons.WARNING,
        )
    
    def info_toast(self, message: str, duration: int = 3):
        """Toast d'information (bleu)"""
        self.show_toast(
            message,
            duration=duration,
            bgcolor="#2196F3",
            icon=ft.Icons.INFO,
        )
    
    # ==================== SNACKBAR ====================
    def show_snackbar(
        self,
        message: str,
        action_label: Optional[str] = None,
        on_action: Optional[Callable] = None,
        duration: int = 4,
        bgcolor: str = "#323232",
    ):
        """
        Affiche une snackbar avec action optionnelle
        
        Args:
            message: Message à afficher
            action_label: Label du bouton d'action
            on_action: Fonction appelée au clic sur l'action
            duration: Durée d'affichage
            bgcolor: Couleur de fond
        """
        snackbar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            action=action_label,
            action_color=ft.Colors.AMBER,
            bgcolor=bgcolor,
            duration=duration * 1000,
        )
        
        if on_action:
            snackbar.on_action = on_action
        
        self.page.snack_bar = snackbar
        snackbar.open = True
        self.page.update()
    
    # ==================== DIALOG CUSTOM ====================
    def custom_dialog(
        self,
        title: Optional[str] = None,
        content: Optional[ft.Control] = None,
        actions: Optional[List[ft.Control]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        modal: bool = True,
        dismissible: bool = True,
    ):
        """
        Dialog personnalisé avec options avancées
        
        Args:
            title: Titre du dialog
            content: Contenu personnalisé
            actions: Liste de boutons
            width: Largeur
            height: Hauteur
            modal: Mode modal
            dismissible: Peut être fermé en cliquant à l'extérieur
        """
        content_widget = content
        
        if width or height:
            content_widget = ft.Container(
                content=content,
                width=width,
                height=height,
            )
        
        dialog = ft.AlertDialog(
            title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD) if title else None,
            content=content_widget,
            actions=actions if actions else [],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=modal,
            shape=ft.RoundedRectangleBorder(radius=10),
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
        
        return dialog
    
    # ==================== DIALOG DE CONFIRMATION ====================
    def confirm_dialog(
        self,
        title: str,
        message: str,
        on_confirm: Callable,
        on_cancel: Optional[Callable] = None,
        confirm_text: str = "Confirmer",
        cancel_text: str = "Annuler",
        confirm_color: str = ft.Colors.RED,
    ):
        """
        Dialog de confirmation avec callbacks
        
        Args:
            title: Titre
            message: Message de confirmation
            on_confirm: Fonction appelée si confirmé
            on_cancel: Fonction appelée si annulé
            confirm_text: Texte du bouton de confirmation
            cancel_text: Texte du bouton d'annulation
            confirm_color: Couleur du bouton de confirmation
        """
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Text(message),
            actions=[
                ft.TextButton(
                    cancel_text,
                    on_click=lambda e: self._close_and_callback(dialog, on_cancel),
                ),
                ft.ElevatedButton(
                    confirm_text,
                    bgcolor=confirm_color,
                    color=ft.Colors.WHITE,
                    on_click=lambda e: self._close_and_callback(dialog, on_confirm),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
        
        return dialog
    
    def _close_and_callback(self, dialog, callback):
        """Ferme le dialog et exécute le callback"""
        dialog.open = False
        self.page.update()
        if callback:
            callback()
    
    # ==================== DIALOG D'ALERTE ====================
    def alert_dialog(
        self,
        title: str,
        message: str,
        type: str = "info",  # "info", "success", "warning", "error"
        ok_text: str = "OK",
        on_ok: Optional[Callable] = None,
    ):
        """
        Dialog d'alerte avec icône selon le type
        
        Args:
            title: Titre
            message: Message
            type: Type d'alerte (info, success, warning, error)
            ok_text: Texte du bouton OK
            on_ok: Callback optionnel
        """
        # Définir l'icône et la couleur selon le type
        icon_map = {
            "info": (ft.Icons.INFO, ft.Colors.BLUE),
            "success": (ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN),
            "warning": (ft.Icons.WARNING, ft.Colors.ORANGE),
            "error": (ft.Icons.ERROR, ft.Colors.RED),
        }
        
        icon, color = icon_map.get(type, (ft.Icons.INFO, ft.Colors.BLUE))
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(icon, color=color, size=28),
                ft.Text(title, weight=ft.FontWeight.BOLD, size=18),
            ], spacing=10),
            content=ft.Text(message, size=14),
            actions=[
                ft.ElevatedButton(
                    ok_text,
                    bgcolor=color,
                    color=ft.Colors.WHITE,
                    on_click=lambda e: self._close_and_callback(dialog, on_ok),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
        
        return dialog
    
    # ==================== DIALOG DE SAISIE ====================
    def input_dialog(
        self,
        title: str,
        label: str,
        on_submit: Callable,
        on_cancel: Optional[Callable] = None,
        hint_text: str = "",
        initial_value: str = "",
        multiline: bool = False,
        password: bool = False,
    ):
        """
        Dialog avec champ de saisie
        
        Args:
            title: Titre
            label: Label du champ
            on_submit: Fonction appelée avec la valeur saisie
            on_cancel: Fonction appelée si annulé
            hint_text: Texte d'aide
            initial_value: Valeur initiale
            multiline: Champ multiligne
            password: Champ mot de passe
        """
        input_field = ft.TextField(
            label=label,
            hint_text=hint_text,
            value=initial_value,
            multiline=multiline,
            password=password,
            autofocus=True,
            width=400,
        )
        
        def submit():
            value = input_field.value
            dialog.open = False
            self.page.update()
            if on_submit:
                on_submit(value)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=input_field,
            actions=[
                ft.TextButton("Annuler", on_click=lambda e: self._close_and_callback(dialog, on_cancel)),
                ft.ElevatedButton(
                    "Valider",
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    on_click=lambda e: submit(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
        
        return dialog
    
    # ==================== LOADING DIALOG ====================
    def loading_dialog(
        self,
        title: str = "Chargement...",
        message: str = "Veuillez patienter",
        height: int = 80,
    ):
        """
        Dialog de chargement avec spinner
        
        Args:
            title: Titre
            message: Message
        """
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text(message, text_align=ft.TextAlign.CENTER),
            ], 
             height=height,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15,
            ),
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
        
        return dialog
    
    def close_dialog(self, dialog):
        """Ferme un dialog"""
        dialog.open = False
        self.page.update()
    
    # ==================== BOTTOM SHEET ====================
    def bottom_sheet(
        self,
        content: ft.Control,
        height: Optional[float] = None,
        dismissible: bool = True,
    ):
        """
        Affiche un bottom sheet (panneau en bas)
        
        Args:
            content: Contenu du bottom sheet
            height: Hauteur
            dismissible: Peut être fermé
        """
        bs = ft.BottomSheet(
            content=ft.Container(
                content=content,
                padding=20,
                height=height,
            ),
            open=True,
            dismissible=dismissible,
        )
        
        self.page.overlay.append(bs)
        bs.open = True
        self.page.update()
        
        return bs
    
    # ==================== DIALOG DE LISTE ====================
    def list_dialog(
        self,
        title: str,
        items: List[dict],  # [{"text": "Item 1", "icon": icon, "on_click": func}, ...]
        width: int = 400,
    ):
        """
        Dialog avec liste d'options cliquables
        
        Args:
            title: Titre
            items: Liste de dictionnaires avec text, icon (optionnel), on_click
            width: Largeur
        """
        list_items = []
        
        for item in items:
            def make_click_handler(dialog, on_click):
                def handler(e):
                    dialog.open = False
                    self.page.update()
                    if on_click:
                        on_click()
                return handler
            
            row_content = []
            if "icon" in item and item["icon"]:
                row_content.append(ft.Icon(item["icon"], size=24))
            row_content.append(ft.Text(item["text"], size=14))
            
            list_item = ft.Container(
                content=ft.Row(row_content, spacing=15),
                padding=15,
                ink=True,
                border_radius=5,
                on_click=None,  # Sera défini après la création du dialog
            )
            list_items.append(list_item)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(list_items, spacing=5, scroll=ft.ScrollMode.AUTO),
                width=width,
            ),
        )
        
        # Assigner les handlers maintenant que le dialog existe
        for i, item in enumerate(items):
            list_items[i].on_click = make_click_handler(dialog, item.get("on_click"))
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
        
        return dialog
