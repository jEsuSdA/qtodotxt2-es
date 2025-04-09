import QtQuick 2.5
import QtQuick.Controls 1.4
import QtQml 2.2

MenuBar {
    Menu {
        title: qsTr("Archivo")
        MenuItem { action: actions.fileNew }
        MenuItem { action: actions.fileOpen}
        Menu {
            id: recentMenu
            title: qsTr("Archivos recientes")
            Instantiator {
                model: mainController.recentFiles
                onObjectAdded: recentMenu.insertItem(index, object)
                onObjectRemoved: recentMenu.removeItem( object )
                delegate: MenuItem {
                    text: (mainController.recentFiles[model.index] ? mainController.recentFiles[model.index] : "")
                    onTriggered: mainController.open(mainController.recentFiles[model.index])
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
        MenuItem { action: actions.quitApp}
        //FIXME: if you want you can play around with the style in ./style/dark_blue/MenuStyle.qml
        //style: MyStyle.MenuStyle{}
    }
    Menu {
        title: qsTr("Acciones")
        MenuItem { action: actions.newTask }
        MenuItem { action: actions.newTaskFrom }
        MenuItem { action: actions.editTask }
        MenuItem { action: actions.deleteTask }
        MenuSeparator {}
        MenuItem { action: actions.completeTasks}
        MenuSeparator {}
        MenuItem { action: actions.increasePriority}
        MenuItem { action: actions.decreasePriority}
    }
    Menu {
        title: qsTr("Ver")
        MenuItem { action: actions.showSearchAction}
        MenuItem { action: actions.showFilterPanel}
        MenuItem { action: actions.showToolBarAction}
        MenuItem { action: actions.showCompleted}
        MenuItem { action: actions.showFuture}
        MenuItem { action: actions.showHidden}
    }
    Menu {
        title: qsTr("Ordenar")
        MenuItem { action: actions.sortDefault}
        MenuItem { action: actions.sortByProjects}
        MenuItem { action: actions.sortByContexts}
        MenuItem { action: actions.sortByDueDate}
    }
    Menu {
        title: qsTr("Ayuda")
        MenuItem { action: actions.helpShowAbout }
    }
}
