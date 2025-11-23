#!/bin/bash

# Script de création du package .deb pour BulletinPro-Prof

APP_NAME="bulletinpro-prof"
APP_VERSION="1.0.0"
ARCH="amd64"
PACKAGE_NAME="${APP_NAME}_${APP_VERSION}_${ARCH}"

echo "📦 Création du package .deb..."

# Créer la structure de répertoires
mkdir -p ${PACKAGE_NAME}/DEBIAN
mkdir -p ${PACKAGE_NAME}/opt/${APP_NAME}
mkdir -p ${PACKAGE_NAME}/usr/share/applications
mkdir -p ${PACKAGE_NAME}/usr/share/icons/hicolor/256x256/apps
mkdir -p ${PACKAGE_NAME}/usr/bin

# Copier les fichiers de l'application
echo "📁 Copie des fichiers..."
cp -r dist/bulletinpro-prof/* ${PACKAGE_NAME}/opt/${APP_NAME}/

# Copier l'icône
cp assets/icons/logo.png ${PACKAGE_NAME}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png

# Créer le fichier de contrôle
cat > ${PACKAGE_NAME}/DEBIAN/control << EOF
Package: ${APP_NAME}
Version: ${APP_VERSION}
Section: education
Priority: optional
Architecture: ${ARCH}
Maintainer: Zeli <contact@bulletinpro.com>
Description: BulletinPro - Gestion de bulletins scolaires
 Application de gestion et génération de bulletins scolaires
 pour les établissements d'enseignement.
 .
 Fonctionnalités:
  - Gestion des élèves
  - Saisie des notes
  - Génération de bulletins
  - Synchronisation cloud
Homepage: https://github.com/yourusername/BulletinPro-Prof
EOF

# Créer le fichier .desktop
cat > ${PACKAGE_NAME}/usr/share/applications/${APP_NAME}.desktop << EOF
[Desktop Entry]
Name=BulletinPro-Prof
Comment=Gestion de bulletins scolaires
Exec=/opt/${APP_NAME}/bulletinpro-prof
Icon=${APP_NAME}
Terminal=false
Type=Application
Categories=Education;Office;
Keywords=bulletin;notes;école;gestion;
StartupWMClass=bulletinpro-prof
EOF

# Créer le script de lancement dans /usr/bin
cat > ${PACKAGE_NAME}/usr/bin/${APP_NAME} << EOF
#!/bin/bash
cd /opt/${APP_NAME}
exec ./bulletinpro-prof "\$@"
EOF

chmod +x ${PACKAGE_NAME}/usr/bin/${APP_NAME}

# Créer le script postinst
cat > ${PACKAGE_NAME}/DEBIAN/postinst << EOF
#!/bin/bash
set -e

# Mettre à jour le cache des icônes
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor
fi

# Mettre à jour le cache des applications
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications
fi

# Rendre l'exécutable accessible
chmod +x /opt/${APP_NAME}/bulletinpro-prof

echo "✅ BulletinPro-Prof installé avec succès!"
echo "Lancez l'application depuis le menu Applications ou avec la commande: ${APP_NAME}"
EOF

chmod +x ${PACKAGE_NAME}/DEBIAN/postinst

# Créer le script prerm
cat > ${PACKAGE_NAME}/DEBIAN/prerm << EOF
#!/bin/bash
set -e

echo "Désinstallation de BulletinPro-Prof..."
EOF

chmod +x ${PACKAGE_NAME}/DEBIAN/prerm

# Définir les permissions correctes
chmod 755 ${PACKAGE_NAME}/DEBIAN
find ${PACKAGE_NAME}/opt/${APP_NAME} -type f -exec chmod 644 {} \;
find ${PACKAGE_NAME}/opt/${APP_NAME} -type d -exec chmod 755 {} \;
chmod +x ${PACKAGE_NAME}/opt/${APP_NAME}/bulletinpro-prof

# Construire le package
echo "🔨 Construction du package..."
dpkg-deb --build --root-owner-group ${PACKAGE_NAME}

echo "✅ Package créé: ${PACKAGE_NAME}.deb"

# Nettoyer
rm -rf ${PACKAGE_NAME}

echo "✨ Terminé!"
