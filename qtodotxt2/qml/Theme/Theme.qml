pragma Singleton
import QtQuick  2.5

QtObject {
    property SystemPalette activePalette: SystemPalette {
        colorGroup: SystemPalette.Active
    }

    property SystemPalette inactivePalette: SystemPalette {
        colorGroup: SystemPalette.Inactive
    }

    property real minRowHeight: 30

    property int mediumSpace: 10
    property int smallSpace: 5
    property int tinySpace: 2

    property string name: "white" // = "dark" or "white"
    property string pathPrefix: "qrc:///" + name + "_icons/resources/" + name + "/" //this will later be sth like qrc:///.../Theme/

    property var mapNameSource: {
        "document-new": "FileNew.svg",
        "document-open": "FileOpen.svg",
        "document-save": "FileSave.svg",
        "list-add": "TaskCreate.svg",
        "new-from": "TaskNewFrom.svg",
        "list-remove": "TaskDelete.svg",
        "document-edit": "TaskEdit.svg",
        "checkmark": "TaskComplete.svg",
        "arrow-up": "TaskPriorityIncrease.svg",
        "arrow-down": "TaskPriorityDecrease.svg",
        "search": "ActionSearch.svg",
        "view-filter": "sidepane.svg",
        "show-completed": "show_completed.svg", 
        "future": "future.svg", 
        "archive": "archive.svg",
        "addLink": "link.svg",
        "help-about": "ApplicationAbout.svg", 
        'qtodotxt-filter-all': 'FilterAll.svg',
        'qtodotxt-filter-uncategorized': 'FilterUncategorized.svg',
        'qtodotxt-filter-due': 'FilterDue.svg',
        'qtodotxt-filter-contexts': 'FilterContexts.svg',
        'qtodotxt-filter-projects': 'FilterProjects.svg',
        'qtodotxt-filter-complete': 'FilterComplete.svg',
        'qtodotxt-filter-due-today': 'FilterDueToday.svg',
        'qtodotxt-filter-due-tomorrow': 'FilterDueTomorrow.svg',
        'qtodotxt-filter-due-week': 'FilterDueWeek.svg',
        'qtodotxt-filter-due-month': 'FilterDueMonth.svg',
        'qtodotxt-filter-due-overdue': 'FilterDueOverdue.svg'
    }

    // resolve icon source path from icon name
    function iconSource(iconName) {
        if (mapNameSource[iconName])
            return pathPrefix + mapNameSource[iconName]
        else return ""
    }
}
