#!/bin/bash

# --- Script de Construcción de Paquete .DEB para QTodoTXT-es ---

# Nombre del paquete (sin espacios, minúsculas, guiones permitidos)
PKG_NAME="qtodotxt-es"
VERSION="20260130" # Puedes cambiar esto por la versión real
ARCH="all"
MAINTAINER="jEsuSdA <info@jesusda.com>"
DESC="Gestor de tareas todo.txt basado en Python y Qt (QML)."

# Directorio temporal de construcción
BUILD_DIR="build_deb"
DEB_NAME="${PKG_NAME}_${VERSION}_${ARCH}.deb"

# Archivos fuente (asumimos que estás en la carpeta que contiene qtodotxt-es/, el icono y el .desktop)
SOURCE_DIR="qtodotxt-es"
ICON_FILE="qtodotxt.png"
DESKTOP_FILE="qtodotxt-es.desktop"

echo ">>> 🏗️  Iniciando construcción del paquete: $DEB_NAME"

# 1. Limpieza previa
rm -rf "$BUILD_DIR"
rm -f "$DEB_NAME"

# 2. Crear estructura de directorios simulada
# DEBIAN -> metadatos
# opt -> aplicación
# usr/share/... -> integración escritorio
# usr/bin -> ejecutable global
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/opt/$PKG_NAME"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/pixmaps"
mkdir -p "$BUILD_DIR/usr/bin"

# 3. Copiar archivos de la aplicación
echo ">>> 📂 Copiando código fuente..."

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Error: No encuentro el directorio '$SOURCE_DIR'."
    exit 1
fi

# Copiamos todo el contenido recursivamente a /opt/qtodotxt-es
cp -r "$SOURCE_DIR"/* "$BUILD_DIR/opt/$PKG_NAME/"

# 4. Limpieza de archivos basura antes de empaquetar
echo ">>> 🧹 Limpiando archivos innecesarios (__pycache__, git, etc)..."
find "$BUILD_DIR/opt/$PKG_NAME" -name "__pycache__" -type d -exec rm -rf {} +
find "$BUILD_DIR/opt/$PKG_NAME" -name "*.pyc" -delete
find "$BUILD_DIR/opt/$PKG_NAME" -name ".git" -type d -exec rm -rf {} +
rm -rf "$BUILD_DIR/opt/$PKG_NAME/venv" # Aseguramos no meter un entorno virtual
rm -f "$BUILD_DIR/opt/$PKG_NAME/uninstall.sh" # No tiene sentido en un .deb

# 5. Crear el lanzador en /usr/bin
# Este script usa el python del sistema para lanzar el script principal en /opt
echo ">>> 🐚 Creando lanzador ejecutable..."
cat > "$BUILD_DIR/usr/bin/$PKG_NAME" << EOL
#!/bin/bash
exec python3 /opt/$PKG_NAME/bin/qtodotxt "\$@"
EOL
chmod 755 "$BUILD_DIR/usr/bin/$PKG_NAME"

# 6. Copiar Icono y .desktop
echo ">>> 🖼️  Integrando recursos gráficos..."
# Tu archivo .desktop dice Icon=qtodotxt, así que copiamos el png con ese nombre
cp "$ICON_FILE" "$BUILD_DIR/usr/share/pixmaps/qtodotxt.png"
cp "$DESKTOP_FILE" "$BUILD_DIR/usr/share/applications/$PKG_NAME.desktop" 

# 7. Generar archivo de CONTROL
# Aquí es donde definimos las dependencias reales del sistema.
# Hemos incluido los módulos QML necesarios detectados en tus imports.
echo ">>> 📝 Generando metadatos (control)..."
cat > "$BUILD_DIR/DEBIAN/control" << EOL
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Depends: python3, python3-pyqt5, python3-dateutil, qml-module-qtquick-controls, qml-module-qtquick-dialogs, qml-module-qtquick-layouts, qml-module-qtquick-window2, qml-module-qt-labs-settings
Maintainer: $MAINTAINER
Description: $DESC
 QTodoTXT-es es una interfaz gráfica moderna para gestionar listas de tareas
 en formato todo.txt. Utiliza Python3 y Qt5 (QML).
EOL

# 8. Scripts Post-Instalación y Post-Eliminación
# Para actualizar caché de iconos y escritorio al instalar/desinstalar
cat > "$BUILD_DIR/DEBIAN/postinst" << EOL
#!/bin/bash
set -e
if [ "\$1" = "configure" ]; then
    update-desktop-database >/dev/null 2>&1 || true
fi
exit 0
EOL
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

cat > "$BUILD_DIR/DEBIAN/postrm" << EOL
#!/bin/bash
set -e
if [ "\$1" = "remove" ] || [ "\$1" = "purge" ]; then
    update-desktop-database >/dev/null 2>&1 || true
fi
exit 0
EOL
chmod 755 "$BUILD_DIR/DEBIAN/postrm"

# 9. Asignar Permisos Finales
# Root debe ser el dueño de todo para evitar problemas de seguridad
chmod -R 755 "$BUILD_DIR/DEBIAN"
chmod -R 755 "$BUILD_DIR/opt"
chmod -R 755 "$BUILD_DIR/usr"

# 10. Construir el paquete
echo ">>> 📦 Empaquetando..."
dpkg-deb --build "$BUILD_DIR" "$DEB_NAME"

# 11. Limpieza
echo ">>> 🗑 Limpieza final..."
rm -rf "$BUILD_DIR"

echo ">>> ✅ ¡Paquete creado con éxito!"
echo "    Archivo: $DEB_NAME"
echo "    Para instalar: sudo dpkg -i $DEB_NAME"
echo "    Si faltan dependencias: sudo apt-get install -f"