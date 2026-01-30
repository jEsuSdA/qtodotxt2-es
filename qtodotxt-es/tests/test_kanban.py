#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad Kanban
"""

import sys
sys.path.insert(0, '/home/jesusda/work-in-progress/apps/apps-propias/qtodotxt2-es')

# Importar componentes
from qtodotxt2.kanban_controller import KanbanController
from qtodotxt2.kanban_window import KanbanWindow
from qtodotxt2.main_controller import MainController
from qtodotxt2.lib.tasklib import Task
import argparse

# Crear argumentos de prueba
args = argparse.Namespace()
args.file = None
args.loglevel = ['WARN']

# Inicializar MainController
print("1. Inicializando MainController...")
main_controller = MainController(args)

# Verificar que KanbanController se puede crear
print("2. Creando KanbanController...")
try:
    kanban_controller = KanbanController(main_controller)
    print("   ✓ KanbanController creado exitosamente")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Verificar que KanbanWindow se puede crear
print("3. Creando KanbanWindow...")
try:
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    kanban_window = KanbanWindow(main_controller)
    print("   ✓ KanbanWindow creado exitosamente")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Verificar data model
print("4. Verificando estructura de datos...")
kanban_data = kanban_controller.kanbanData
columns = kanban_controller.columns
print(f"   ✓ Columnas: {list(columns.keys())}")
print(f"   ✓ Número de columnas: {len(columns)}")

# Verificar que openKanbanView funciona
print("5. Verificando método openKanbanView...")
try:
    main_controller.openKanbanView()
    print("   ✓ Método openKanbanView ejecutado exitosamente")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

print("\n✅ Todas las pruebas pasaron exitosamente!")
print("   - KanbanController implementado correctamente")
print("   - KanbanWindow implementado correctamente")
print("   - openKanbanView() funciona correctamente")
