import QtQuick 2.5
import QtQuick.Controls 1.4
import QtQuick.Dialogs 1.1
import Qt.labs.settings 1.0

import Theme 1.0

Item {
    id: actions

    Settings {
        category: "VisibleWidgets"
        property alias search_field_visible: showSearchAction.checked
        property alias toolbar_visible: showToolBarAction.checked
        property alias filter_panel_visible: showFilterPanel.checked
        property alias show_completed: showCompleted.checked
        property alias show_future: showFuture.checked
        property alias show_hidden: showHidden.checked
    }

    property Action fileNew: Action{
            iconName: "document-new"
            text: qsTr("Nuevo Archivo")
            //shortcut: StandardKey.New
            onTriggered: {        }
    }

    property Action fileOpen: Action {
        iconName: "document-open"
        text: qsTr("Abrir Archivo")
        shortcut: StandardKey.Open
        enabled: !taskListView.editing
        onTriggered: {
            fileDialog.selectExisting = true
            fileDialog.open()
        }
    }

    property Action fileSave: Action{
        iconName: "document-save"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Guardar Archivo")
        shortcut: StandardKey.Save
        enabled: !taskListView.editing
        onTriggered: mainController.save()
    }

    property Action fileSaveAs: Action{
        iconName: "document-save-as"
        text: qsTr("Guardar Archivo como...")
        shortcut: StandardKey.SaveAs
        enabled: !taskListView.editing
        onTriggered: {
            fileDialog.selectExisting = false
            fileDialog.open()
        }
    }

    property Action quitApp: Action{
        iconName: "application-exit"
        text: qsTr("Salir")
        shortcut: StandardKey.Quit
        onTriggered: appWindow.close()
    }

    property Action newTask: Action{
        iconName: "list-add"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Añadir nueva Tarea")
        shortcut: "Ins"|StandardKey.New
        enabled: !taskListView.editing
        onTriggered: {
            taskListView.newTask('')
        }
    }

    property Action newTaskFrom: Action{
        iconName: "new-from"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Añadir nueva Tarea desde plantilla")
        enabled: !taskListView.editing && taskListView.currentItem !== null
        onTriggered: {
            taskListView.newFromTask();
        }
    }

    property Action deleteTask: Action{
        iconName: "list-remove"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Eliminar Tarea")
        shortcut: "Del"
        enabled: !taskListView.editing && taskListView.currentItem !== null
        onTriggered: taskListView.deleteSelectedTasks()
    }

    property Action editTask: Action{
        iconName: "document-edit"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Editar Tarea")
        shortcut: "Ctrl+E"
        enabled: !taskListView.editing && taskListView.currentItem !== null
        onTriggered: { taskListView.editCurrentTask() }
    }

    property Action completeTasks: Action{
        iconName: "checkmark"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Marcar Tarea como completada")
        shortcut: "X"
        enabled: !taskListView.editing && taskListView.currentItem !== null
        onTriggered: {
            taskListView.storeSelection()
            mainController.completeTasks(taskListView.getSelectedIndexes())
            taskListView.restoreSelection()
        }
    }

    property Action increasePriority: Action{
        iconName: "arrow-up"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Incrementar Prioridad")
        shortcut: "+"
        enabled: !taskListView.editing && taskListView.currentItem !== null
        onTriggered: {
            taskListView.storeSelection()
            taskListView.currentItem.task.increasePriority()
            taskListView.restoreSelection()
        }
    }

    property Action decreasePriority: Action{
        iconName: "arrow-down"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Disminuir Prioridad")
        shortcut: "-"
        enabled: !taskListView.editing && taskListView.currentItem !== null
        onTriggered: {
            taskListView.storeSelection()
            taskListView.currentItem.task.decreasePriority()
            taskListView.restoreSelection()
        }
    }

    property Action showSearchAction: Action{
        id: showSearchAction
        iconName: "search"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Mostrar campo de Búsqueda")
        shortcut: "Ctrl+F"
        checkable: true
    }

    property Action showFilterPanel: Action{
        id: showFilterPanel
        iconName: "view-filter"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Mostrar panel de Filtros")
        checkable: true
        checked: true
    }

    property Action showToolBarAction: Action{
        id: showToolBarAction
        iconName: "configure-toolbars"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Mostrar Barra de Herramientas")
        shortcut: "Ctrl+T"
        checkable: true
        checked: true
    }

    property Action showCompleted: Action{
        id: showCompleted
        iconName: "show-completed"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Mostrar Tareras Completadas")
        shortcut: "Ctrl+C"
        checkable: true
        checked: false
        enabled: !taskListView.editing
        onToggled: {
            taskListView.storeSelection()
            mainController.showCompleted = checked
            taskListView.restoreSelection()
        }
    }

    property Action showFuture: Action{
        id: showFuture
        iconName: "future"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Mostrar Tareas Futuras")
        shortcut: "Ctrl+F"
        checkable: true
        checked: true
        enabled: !taskListView.editing
        onToggled: {
            taskListView.storeSelection()
            mainController.showFuture = checked
            taskListView.restoreSelection()
        }
    }

    property Action showHidden: Action{
        id: showHidden
        iconName: "show-hidden"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Mostrar Tareas Ocultas")
        shortcut: "Ctrl+H"
        checkable: true
        checked: false
        enabled: !taskListView.editing
        onToggled: {
            taskListView.storeSelection()
            mainController.showHidden = checked
            taskListView.restoreSelection()
        }
    }

    property Action archive: Action{
        iconName: "archive"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Archivar Tareas Completadas")
        shortcut: "Ctrl+A"
        enabled: !taskListView.editing
        onTriggered: {
            taskListView.storeSelection()
            mainController.archiveCompletedTasks()
            taskListView.restoreSelection()
        }
    }

    property Action addLink: Action{
        iconName: "addLink"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Añadir Enlace a la Tarea actual")
        shortcut: "Ctrl+L"
        enabled: !taskListView.editing && taskListView.currentItem !== null
        onTriggered: linkDialog.open()
    }

    property Action helpShowAbout: Action{
        iconName: "help-about"
        iconSource: Theme.iconSource(iconName)
        text: qsTr("Acerca de");
        shortcut: "F1"
        onTriggered: {
            var component = Qt.createComponent("AboutBox.qml")
            var dialog = component.createObject(appWindow)
            dialog.open()
        }
    }

    property Action helpShowShortcuts: Action{
        iconName: "help-about"
        text: qsTr("Lista de Atajos de Teclado");
        shortcut: "Ctrl+F1"
        onTriggered: aboutBox.open()
    }

    property Action sortDefault: Action{
        iconName: "view-sort-ascending-symbolic"
        text: "Por Defecto"
        enabled: !taskListView.editing
        onTriggered: {
            taskListView.storeSelection()
            mainController.sortingMode = "default"
            taskListView.restoreSelection()
        }
    }

    property Action sortByProjects: Action{
        iconName: "view-sort-ascending-symbolic"
        text: "Proyectos"
        enabled: !taskListView.editing
        onTriggered: {
            taskListView.storeSelection()
            mainController.sortingMode = "projects"
            taskListView.restoreSelection()
        }
    }

    property Action sortByContexts: Action{
        iconName: "view-sort-ascending-symbolic"
        text: "Contextos"
        enabled: !taskListView.editing
        onTriggered: {
            taskListView.storeSelection()
            mainController.sortingMode = "contexts"
            taskListView.restoreSelection()
        }
    }

    property Action sortByDueDate: Action{
        //id:sortDueDate
        iconName: "view-sort-ascending-symbolic"
        text: "Fecha de Vencimiento"
        enabled: !taskListView.editing
        onTriggered: {
            taskListView.storeSelection()
            mainController.sortingMode = "due"
            taskListView.restoreSelection()
        }
    }

    FileDialog {
        id: fileDialog
        nameFilters: ["Text files (*.txt)"]
        folder: mainController.docPath
        onAccepted: {
            if (fileDialog.selectExisting) {
                mainController.open(fileUrl)
            } else {
                mainController.save(fileUrl)
            }
        }
    }

    FileDialog {
        id: linkDialog
        selectExisting: true
        onAccepted: {
            taskListView.storeSelection()
            var path = fileUrl.toString()
            path = path.replace(/ /g, "%20")
            taskListView.currentItem.task.text += ' ' + path
            taskListView.restoreSelection()
        }
    }
}

