import logging
import re
from PyQt5 import QtCore

logger = logging.getLogger(__name__)


class KanbanController(QtCore.QObject):
    """Controller that manages Kanban board data and logic for project-based layout"""

    kanbanDataChanged = QtCore.pyqtSignal()

    def __init__(self, main_controller):
        super().__init__()
        self._main = main_controller
        self._kanban_data = {}

        self._columns = {
            'NP': 'Bandeja de Entrada',
            'D': 'Próximas · D',
            'C': 'Este Mes · C',
            'B': 'Esta Semana · B',
            'A': 'Hacer Hoy · A'
        }
        self._kanban_priorities = ['A', 'B', 'C', 'D']

        # Debounce: regenerar kanban una sola vez aunque lleguen muchos cambios seguidos
        self._rebuild_timer = QtCore.QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(250)  # 200-400ms suele ir bien
        self._rebuild_timer.timeout.connect(self._rebuild_now)

        # Conexiones (evita duplicados si reutilizas la instancia)
        try:
            self._main._file.fileModified.disconnect(self._schedule_rebuild)
        except Exception:
            pass
        try:
            self._main.fileExternallyModified.disconnect(self._schedule_rebuild)
        except Exception:
            pass

        self._main._file.fileModified.connect(self._schedule_rebuild)
        self._main.fileExternallyModified.connect(self._schedule_rebuild)

        # Primer build
        self._generate_kanban_data()

    @QtCore.pyqtProperty('QVariant', notify=kanbanDataChanged)
    def kanbanData(self):
        return self._kanban_data

    @QtCore.pyqtProperty('QVariant')
    def columns(self):
        return self._columns

    # -------------------------
    # Debounce rebuild
    # -------------------------
    def _schedule_rebuild(self, *args, **kwargs):
        # Reinicia el timer: muchos cambios -> 1 rebuild
        self._rebuild_timer.start()

    def _rebuild_now(self):
        self._generate_kanban_data()
        self.kanbanDataChanged.emit()

    # -------------------------
    # Data generation
    # -------------------------
    def _generate_kanban_data(self):
        """Generate kanban data structure for project-based layout (task can appear in multiple projects)."""
        projects = {}
        kanban_priorities = self._kanban_priorities
        all_tasks = self._main.allTasks

        for line_index, task in enumerate(all_tasks):
            # Filtra prioridades fuera de A-D (pero permite vacío => NP)
            priority = task.priority if hasattr(task, 'priority') else ''
            if priority and priority not in kanban_priorities:
                continue

            bucket = 'NP' if priority == '' else priority

            # Lista de proyectos: la tarea debe aparecer en TODOS sus proyectos
            project_names = []
            if hasattr(task, 'projects') and task.projects:
                for proj in task.projects:
                    if proj and proj.strip():
                        project_names.append(proj.strip())

            if not project_names:
                project_names = ['(Sin Proyecto)']
            else:
                # Mantener orden y evitar duplicados
                seen = set()
                ordered = []
                for p in project_names:
                    if p not in seen:
                        seen.add(p)
                        ordered.append(p)
                project_names = ordered

            base_payload = {
                'text': task.text,
                'priority': priority,
                'is_done': task.is_complete if hasattr(task, 'is_complete') else False,
                'line_index': line_index,
                'contexts': getattr(task, 'contexts', []),
                'projects': getattr(task, 'projects', [])
            }

            # Inserta la tarea en cada proyecto
            for project_name in project_names:
                if project_name not in projects:
                    projects[project_name] = {
                        'tasks': {prio: [] for prio in (['NP'] + kanban_priorities)},
                        'max_priority_level': -1
                    }

                # IMPORTANTE: copia del dict para no compartir referencia entre proyectos
                projects[project_name]['tasks'][bucket].append(dict(base_payload))

        # Calcula max_priority_level
        priority_levels = {prio: idx for idx, prio in enumerate(reversed(kanban_priorities))}
        for project_name, project_data in projects.items():
            max_level = -1
            for prio in kanban_priorities:
                if project_data['tasks'][prio]:
                    lvl = priority_levels[prio]
                    if lvl > max_level:
                        max_level = lvl
            project_data['max_priority_level'] = max_level

        # Ordena proyectos por “nivel más alto”
        sorted_projects = dict(sorted(
            projects.items(),
            key=lambda x: (x[1]['max_priority_level'], x[0]),
            reverse=True
        ))

        # Mueve (Sin Proyecto) al final
        if '(Sin Proyecto)' in sorted_projects:
            sin_proyecto = sorted_projects.pop('(Sin Proyecto)')
            sorted_projects['(Sin Proyecto)'] = sin_proyecto

        self._kanban_data = sorted_projects

    # -------------------------
    # Mutations coming from Kanban
    # -------------------------
    def update_task_priority(self, line_index, new_priority):
        """Update task priority by modifying task text (priority property is read-only)."""
        task = self._main.allTasks[line_index]
        text = task.text

        # Remove existing priority
        if re.match(r'^\([A-Z]\) ', text):
            text = text[4:]  # Remove '(A) '

        # Add new priority if not NP
        if new_priority != 'NP':
            text = f'({new_priority}) {text}'

        task.text = text

        # Guardar sin bloquear reentrando en el mismo tick
        QtCore.QTimer.singleShot(0, self._main.save)

    def toggle_task_done(self, line_index, is_done):
        """Toggle task completion status."""
        task = self._main.allTasks[line_index]
        if is_done:
            task.setCompleted()
        else:
            task.setPending()

        QtCore.QTimer.singleShot(0, self._main.save)
