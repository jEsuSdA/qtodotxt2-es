import QtQuick 2.5
import QtQuick.Dialogs 1.2
import QtQuick.Controls 1.4
import Qt.labs.settings 1.0

Dialog {
    id: prefWindow
    Settings {
        category: "Preferences"
        property alias auto_save: autoSaveCB.checked
        property alias auto_reload: autoReloadCB.checked
        property alias singleton: singletonCB.checked
        property alias lowest_priority: lowestPriorityField.text
        property alias add_creation_date: creationDateCB.checked
        property alias match_only_beginnings_of_words_when_filtering: matchOnlyBeginningsOfWordsWhenFilteringCB.checked
    }
    GroupBox {
        Column {
            spacing: 10
            CheckBox { 
                id: singletonCB
                text: qsTr("Una sola instancia") 
                checked: false
            }
            CheckBox { 
                id: autoSaveCB
                text: qsTr("Autoguardado") 
                checked: true
            }
            CheckBox {
                id: autoReloadCB
                text: qsTr("Auto-recarga")
                checked: false
            }
            CheckBox {
                id:creationDateCB
                text: qsTr("Añadir fecha de creación")
                checked: false
            }
            CheckBox {
                id:matchOnlyBeginningsOfWordsWhenFilteringCB
                text: qsTr("Filtrar teniendo en cuenta sólo el inicio de las palabras")
                checked: true
            }
            Row { 
                Label {text: "Prioridad más baja:"}
                TextField { 
                    id: lowestPriorityField; 
                    text: "D"; 
                    inputMask: "A" 
                }
            }
        }
    }
    standardButtons:StandardButton.Ok
    onVisibleChanged: if (visible === false) destroy()
}
