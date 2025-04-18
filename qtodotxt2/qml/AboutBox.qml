import QtQuick 2.5
import QtQuick.Controls 1.4
import QtQuick.Dialogs 1.2

Dialog {
    width: 640
    title: "About QTodoTxt2"
    id: aboutdialog

    Text {
        wrapMode: Text.WordWrap
        width: aboutdialog.width
        text: '<h1>About QTodoTxt2 </h1>
<p>QTodoTxt2 is a cross-platform UI client for todo.txt files
 (see <a href="http://todotxt.com">http://todotxt.com</a>)</p>
2015-2017 Copyright &copy; QTT Development Team<br/>
2025 Copyright &copy; jEsuSdA 8)<br/>
<h2>Links</h2>
<ul>
<li>Project Page: <a href="https://github.com/QTodoTxt/QTodoTxt2">https://github.com/QTodoTxt/QTodoTxt2</a></li>
<li>Project Page of the first version which is no longer maintained: <a href="https://github.com/QTodoTxt/QTodoTxt">https://github.com/QTodoTxt/QTodoTxt</a></li>
</ul>
<h2>Credits</h2>
<ul>
    <li>Concept by <a href="http://ginatrapani.org/">Gina Trapani</a></li>
    <li>Icons by <a href="http://tango.freedesktop.org/">The Tango! Desktop Project</a>
        and <a href="http://www.famfamfam.com/lab/icons/silk/">Mark James</a></li>
    <li>Original code by <a href="http://elentok.blogspot.com">David Elentok</a></li>
    <li>Versión con correcciones, mejoras menores y traducida al Español por <a href="https://www.jesusda.com">jEsuSdA 8)</a></li>
</ul>
<h2>License</h2>
<p>This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.</p>
<p>This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.</p>
<p>You should have received a copy of the GNU General Public License
along with this program.  If not, see
<a href="http://www.gnu.org/licenses/">http://www.gnu.org/licenses/</a>.</p>
'
        onLinkActivated: Qt.openUrlExternally(link)

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.NoButton
            cursorShape: parent.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor
        }
    }
    standardButtons: StandardButton.Ok
    onVisibleChanged: if (visible === false) destroy()
    Component.onDestruction: console.log("Tschüüüs.")
}
