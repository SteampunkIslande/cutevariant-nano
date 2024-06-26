import PySide6.QtWidgets as qw


class MultiWidgetHolder(qw.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()
        self.setLayout(self._layout)

        self.widgets: dict[str, qw.QWidget] = {}
        self.current_widget: qw.QWidget = None
        self.current_widget_name: str = None

    def add_widget(self, widget: qw.QWidget, name: str):
        self.widgets[name] = widget
        if not self.current_widget:
            self.set_current_widget(name)
            self.current_widget_name = name

    def remove_widget(self, name: str):
        widget = self.widgets.pop(name)
        if self.current_widget is widget:
            self.current_widget = None
            self.current_widget_name = None
        widget.hide()
        self._layout.removeWidget(widget)
        widget.deleteLater()

    def get_current_widget_name(self):
        return self.current_widget_name

    def set_current_widget(self, name: str):
        if name not in self.widgets:
            return
        if self.current_widget is self.widgets[name]:
            return
        if self.current_widget:
            self._layout.replaceWidget(self.current_widget, self.widgets[name])
            self.current_widget.hide()
        else:
            self._layout.addWidget(self.widgets[name])

        self.current_widget = self.widgets[name]
        self.current_widget_name = name
        self.current_widget.show()
