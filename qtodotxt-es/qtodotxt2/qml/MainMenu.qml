import QtQuick 2.5
import QtQuick.Controls 1.4
import QtQml 2.2
import "Theme" as Theme

MenuBar {
    id: root

    // =========================
    // NULL OBJECT (fallback) -> como PROPIEDAD (no como hijo de MenuBar)
    // =========================
    property QtObject nullMain: QtObject {
        property var recentFiles: []
        function open(path) { /* noop */ }
        function openKanbanView() { /* noop */ }
    }

    // Controller seguro
    property var mc: (mainController !== null && mainController !== undefined) ? mainController : nullMain

    Menu {
        title: qsTr("Archivo")
        MenuItem { action: actions.fileNew }
        MenuItem { action: actions.fileOpen }

        Menu {
            id: recentMenu
            title: qsTr("Archivos recientes")

            Instantiator {
                model: mc.recentFiles
                onObjectAdded: recentMenu.insertItem(index, object)
                onObjectRemoved: recentMenu.removeItem(object)

                delegate: MenuItem {
                    text: (mc.recentFiles[index] ? mc.recentFiles[index] : "")
                    onTriggered: {
                        var f = mc.recentFiles[index]
                        if (f) mc.open(f)
                    }
                }
            }
        }

        MenuItem { action: actions.fileSave }
        MenuSeparator {}

        MenuItem {
            text: qsTr("Preferencias")
            iconName: "configure"
            onTriggered: {
                var component = Qt.createComponent("Preferences.qml")
                var dialog = component.createObject(component.prefWindow)
                dialog.open()
            }
        }

        MenuSeparator {}
        MenuItem { action: actions.quitApp }
    }

    Menu {
        title: qsTr("Acciones")
        MenuItem { action: actions.newTask }
        MenuItem { action: actions.newTaskFrom }
        MenuItem { action: actions.editTask }
        MenuItem { action: actions.deleteTask }
        MenuSeparator {}
        MenuItem { action: actions.completeTasks }
        MenuSeparator {}
        MenuItem { action: actions.increasePriority }
        MenuItem { action: actions.decreasePriority }
    }

    Menu {
        title: qsTr("Ver")
        MenuItem { action: actions.showSearchAction }
        MenuItem { action: actions.showFilterPanel }
        MenuItem { action: actions.showToolBarAction }
        MenuItem { action: actions.showCompleted }
        MenuItem { action: actions.showFuture }
        MenuItem { action: actions.showHidden }
        MenuSeparator {}
        MenuItem {
            text: qsTr("Tablero Kanban")
            iconSource: "qrc:///white_icons/resources/white/Kanban.svg"
            onTriggered: mc.openKanbanView()
        }
    }

    Menu {
        title: qsTr("Ordenar")
        MenuItem { action: actions.sortDefault }
        MenuItem { action: actions.sortByProjects }
        MenuItem { action: actions.sortByContexts }
        MenuItem { action: actions.sortByDueDate }
    }

    Menu {
        title: qsTr("Ayuda")
        MenuItem { action: actions.helpShowAbout }
    }
}
