#!/usr/bin/env python


from functools import partial
from typing import List, Union

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

import app as ap
import query.query_component as q_cmpt
import query.query_table_model as q_tm
from common_widgets.any_widget_dialog import AnyWidgetDialog
from filters import filters_component as f_cmpt


class PageSelector(qw.QWidget):

    def __init__(self, app: ap.App, query: "q_cmpt.QueryComponent", parent=None):
        super().__init__(parent)

        self.app = app
        self.query = query

        # TODO: rows line edit: setValidator: range should be user defined...

        self.rows_label = qw.QLabel(self.app.translate("Rows per page"))
        self.rows_lineedit = qw.QLineEdit()
        self.rows_lineedit.setText("10")
        self.rows_lineedit.setValidator(qg.QIntValidator(1, 100))
        self.rows_lineedit.textChanged.connect(self.set_rows_per_page)

        self.spacer = qw.QSpacerItem(
            40, 20, qw.QSizePolicy.Policy.Expanding, qw.QSizePolicy.Policy.Minimum
        )
        self.first_page_button = qw.QPushButton("<<")
        self.first_page_button.clicked.connect(self.goto_first_page)
        self.prev_button = qw.QPushButton("<")
        self.prev_button.clicked.connect(self.goto_previous_page)
        self.page_label = qw.QLabel(self.app.translate("Page"))
        self.page_lineedit = qw.QLineEdit()
        self.page_lineedit.setFixedWidth(50)
        self.page_lineedit.setText("1")
        self.page_lineedit.setValidator(qg.QIntValidator(1, 1))
        self.page_lineedit.textChanged.connect(self.set_page)
        self.page_count_label = qw.QLabel(self.app.translate("out of (unknown)"))
        self.next_button = qw.QPushButton(">")
        self.next_button.clicked.connect(self.goto_next_page)
        self.last_page_button = qw.QPushButton(">>")
        self.last_page_button.clicked.connect(self.goto_last_page)

        self.query.query_changed.connect(self.update_page_selector)

        self.setup_layout()

    def setup_layout(self):
        layout = qw.QHBoxLayout()
        layout.addWidget(self.rows_label)
        layout.addWidget(self.rows_lineedit)
        layout.addItem(self.spacer)
        layout.addWidget(self.first_page_button)
        layout.addWidget(self.prev_button)
        layout.addWidget(self.page_label)
        layout.addWidget(self.page_lineedit)
        layout.addWidget(self.page_count_label)
        layout.addWidget(self.next_button)
        layout.addWidget(self.last_page_button)
        self.setLayout(layout)

    def goto_first_page(self):
        self.query.first_page().commit()

    def goto_previous_page(self):
        self.query.previous_page().commit()

    def goto_next_page(self):
        self.query.next_page().commit()

    def goto_last_page(self):
        self.query.last_page().commit()

    def update_page_selector(self):
        # Block signals to avoid infinite loops
        self.page_lineedit.blockSignals(True)
        self.rows_lineedit.blockSignals(True)

        self.rows_lineedit.setText(str(self.query.get_limit()))
        self.page_lineedit.setText(str(self.query.get_page()))

        self.page_lineedit.setValidator(
            qg.QIntValidator(1, self.query.get_page_count())
        )
        self.page_count_label.setText(
            self.app.translate("out of {}").format(self.query.get_page_count())
        )

        self.page_lineedit.blockSignals(False)
        self.rows_lineedit.blockSignals(False)

    def set_page(self, page):
        self.query.set_page(int(page) if page else 1).commit()

    def set_rows_per_page(self, rows_per_page):
        self.query.set_limit(int(rows_per_page or 10)).commit()


class QueryTableProxyModel(qc.QSortFilterProxyModel):

    def __init__(
        self,
        parent: qc.QObject = None,
    ):
        super().__init__(parent)
        self.selected_fields = []

    # Automatically hides columns which names start with a dot
    def filterAcceptsColumn(self, source_column: int, source_parent: qc.QModelIndex):
        source_model = self.sourceModel()
        colname: str = source_model.headerData(
            source_column, qc.Qt.Orientation.Horizontal
        )

        # If the column name starts with a dot, hide it
        # If self.selected_fields is empty, show all non-hidden columns
        return not colname.startswith(".") and (
            colname in self.selected_fields or (not self.selected_fields)
        )

    def update_selected_fields(self, fields: List[str]):
        self.selected_fields = fields
        self.invalidateFilter()


class QueryTableWidget(qw.QWidget):

    # Add signal that updates when selected rows change
    selection_changed = qc.Signal()

    def __init__(self, app: ap.App, query: "q_cmpt.QueryComponent", parent=None):
        super().__init__(parent)

        self.app = app
        self.query = query

        self.query_model = q_tm.QueryTableModel(self.query)
        self.proxy_model = QueryTableProxyModel()
        self.proxy_model.setSourceModel(self.query_model)

        self.table_view = qw.QTableView()
        self.table_view.setSelectionBehavior(
            qw.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_view.horizontalHeader().setStretchLastSection(
            True
        )  # Set last column to expand
        self.table_view.horizontalHeader().setContextMenuPolicy(
            qg.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.table_view.horizontalHeader().customContextMenuRequested.connect(
            self.show_header_context_menu
        )
        self.table_view.setContextMenuPolicy(qg.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_table_context_menu)
        self.table_view.setModel(self.proxy_model)

        self.table_view.selectionModel().selectionChanged.connect(
            self.selection_changed
        )

        self.page_selector = PageSelector(self.app, self.query)

        layout = qw.QVBoxLayout()
        layout.addWidget(self.table_view)
        layout.addWidget(self.page_selector)

        self.setLayout(layout)

    def get_current_validation_hashes(self) -> list[int | None]:
        selected_rows = self.table_view.selectionModel().selectedRows()
        if selected_rows:

            return [
                index.data(qc.Qt.ItemDataRole.UserRole)[".validation_hash"]
                for index in selected_rows
            ]

    def show_header_context_menu(self, pos):
        menu = qw.QMenu()

        index = self.table_view.indexAt(pos)

        filter_action = menu.addAction(
            self.app.translate("Filter this column (simple expression)")
        )
        filter_action.triggered.connect(partial(self.filter_column, index))

        order_action: qg.QAction = menu.addAction(
            self.app.translate("Sort this column")
        )
        order_action.triggered.connect(partial(self.add_order_by, index))

        menu.exec(self.table_view.mapToGlobal(pos))

    def add_order_by(self, index: qc.QModelIndex):
        self.query.add_order_by(
            self.proxy_model.headerData(index.column(), qc.Qt.Orientation.Horizontal),
            "ASC",
        ).commit()

    def show_table_context_menu(self, pos):
        menu = qw.QMenu()

        index = self.table_view.indexAt(pos)

        if not index.data(qc.Qt.ItemDataRole.UserRole):
            return

        debug_action: qg.QAction = menu.addAction(
            self.app.translate("(DEBUG) Show underlying data for this line")
        )
        debug_action.triggered.connect(partial(self.show_row_userdata, index))

        add_variant_action: qg.QAction = menu.addAction(
            self.app.translate("Add variant to validation")
        )
        add_variant_action.triggered.connect(self.add_variant_to_validation)

        # Neutralize Goto Mobidetails action
        # goto_mobidetails_action: qg.QAction = menu.addAction(
        #     self.app.translate("Browse variant in Mobidetails")
        # )
        # goto_mobidetails_action.triggered.connect(partial(self.goto_mobidetails, index))

        copy_action: qg.QAction = menu.addAction(self.app.translate("Copy"))
        copy_action.triggered.connect(partial(self.copy_current_row, index))
        copy_action.setShortcut("Ctrl+C")

        menu.exec(qg.QCursor.pos())

    def copy_current_row(self, index: qc.QModelIndex):
        qg.QGuiApplication.clipboard().setText(
            index.data(qc.Qt.ItemDataRole.DisplayRole) or ""
        )

    def add_variant_to_validation(self):
        payload = {"validation_infos": []}
        for index in self.table_view.selectionModel().selectedRows(0):
            row_data: dict[str, Union[str | int]] = index.data(
                qc.Qt.ItemDataRole.UserRole
            )
            sample_name = row_data[".sample_name"]
            run_name = row_data[".run_name"]
            transcript_id = row_data[".nm"]
            variant_hash = row_data[".variant_hash"]

            val_table_uuid = self.query.get_editable_table_name()
            validation_hash = row_data[".validation_hash"]

            payload["validation_infos"].append(
                {
                    "table_uuid": val_table_uuid,
                    "validation_hash": validation_hash,
                    "sample_name": sample_name,
                    "run_name": run_name,
                    "transcript_ID": transcript_id,
                    "variant_hash": variant_hash,
                    "accepted": True,
                }
            )
        self.query.add_variant_to_validation(payload)

    def show_row_userdata(self, index: qc.QModelIndex):
        row_data: dict = index.data(qc.Qt.ItemDataRole.UserRole)
        if not row_data:
            return

        table_widget = qw.QTableView()
        simple_model = qg.QStandardItemModel(0, 2)
        simple_model.setHorizontalHeaderLabels(
            [
                self.app.translate("Column name"),
                self.app.translate("Column value"),
            ]
        )
        for key, value in row_data.items():
            key_item = qg.QStandardItem(key)
            key_item.setEditable(False)

            value_item = qg.QStandardItem(str(value))
            value_item.setEditable(False)

            simple_model.appendRow([key_item, value_item])
        table_widget.setModel(simple_model)
        table_widget.horizontalHeader().setStretchLastSection(True)
        table_widget.horizontalHeader().setSectionResizeMode(
            0, qw.QHeaderView.ResizeMode.ResizeToContents
        )
        table_widget.horizontalHeader().setSectionResizeMode(
            1, qw.QHeaderView.ResizeMode.Stretch
        )
        # Smooth scrolling
        table_widget.setHorizontalScrollMode(
            qw.QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        table_widget.verticalHeader().setVisible(False)
        table_widget.setSelectionMode(
            qw.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        table_widget.setSelectionBehavior(
            qw.QAbstractItemView.SelectionBehavior.SelectRows
        )

        dialog = AnyWidgetDialog(
            table_widget,
            self.app.translate("Underlying data"),
            self,
            add_stretch=False,
        )
        dialog.exec()

    def goto_mobidetails(self, index: qc.QModelIndex):
        import requests

        def mobidetails_get(nc, position, reference, alternate, **kwargs):
            position = int(position)
            base = "https://mobidetails.iurc.montp.inserm.fr/MD/api/variant/exists"
            if len(reference) > len(alternate):
                # Deletion
                q = f"{base}/{nc}:g.{position}_{position+len(reference)-len(alternate)+1}del"
            elif len(reference) < len(alternate):
                # Insertion
                q = f"{base}/{nc}:g.{position}_{position+1}ins{alternate[1:]}"
            else:
                # Substitution
                q = f"{base}/{nc}:g.{position}{reference}>{alternate}"
            res = requests.get(q)
            if res.status_code == 200:
                return res.json()
            return {}

        row_data: dict[str] = index.data(qc.Qt.ItemDataRole.UserRole)
        nc = row_data.get(".NC", None)
        position = row_data.get(".Position", None)
        reference = row_data.get(".Allèle de référence", None)
        alternate = row_data.get(".Allèle alternatif", None)
        if all((nc, position, reference, alternate)):
            res = mobidetails_get(nc, position, reference, alternate)
            if "mobidetails_id" in res:
                qg.QDesktopServices.openUrl(
                    qc.QUrl(
                        f"https://mobidetails.iurc.montp.inserm.fr/MD/api/variant/{res['mobidetails_id']}/browser/"
                    )
                )
            else:
                qw.QMessageBox.warning(
                    self,
                    self.app.translate("Mobidetails"),
                    self.app.translate("Cannot find variant on Mobidetails"),
                )

    def update_selected_fields(self, fields: list[str]):
        self.proxy_model.update_selected_fields(fields)

    def filter_column(self, index: qc.QModelIndex):

        col_name = index.model().headerData(
            index.column(), qc.Qt.Orientation.Horizontal
        )
        dialog = SimpleFilterDialog(
            self.app, self.query.get_column_info(col_name), self
        )

        if dialog.exec() == qw.QDialog.DialogCode.Accepted:
            filter_text = dialog.get_filter()
            filter_component: f_cmpt.FiltersComponent = self.app.get_component(
                "filters", self.query.get_instance_name() + "/filters"
            )
            if not filter_component:
                return
            filter_component.add_expression(filter_text)


class SimpleFilterDialog(qw.QDialog):

    def __init__(self, app: ap.App, col_info: dict, parent=None):
        super().__init__(parent)

        self.col_info = col_info
        self.app = app

        self.setWindowTitle(self.app.translate("Filter a column"))

        # Create widgets
        # Create a label for the column name
        # Create a combo box for the operator (according to the column type)
        # Create a line edit for the value
        # Create a button box with OK and Cancel buttons

        self._layout = qw.QFormLayout()

        self._col_name_label = qw.QLabel(col_info["name"])
        self._operator_combo = qw.QComboBox()

        operators = [
            (self.app.translate("equal to"), "="),
            (self.app.translate("not equal to"), "!="),
            (self.app.translate("is null"), "IS NULL"),
            (self.app.translate("is not null"), "IS NOT NULL"),
        ]

        if self.col_info["type"] not in ("VARCHAR", "TEXT"):
            operators += [
                (self.app.translate("greater than"), ">"),
                (self.app.translate("greater than or equal to"), ">="),
                (self.app.translate("less than"), "<"),
                (self.app.translate("less than or equal to"), "<="),
            ]
        else:
            operators += [
                (self.app.translate("regex matches"), "SIMILAR TO"),
                (self.app.translate("regex does not match"), "NOT SIMILAR TO"),
            ]

        for label, operator in operators:
            self._operator_combo.addItem(label, operator)

        self._value_le = qw.QLineEdit()

        self._button_box = qw.QDialogButtonBox(
            qw.QDialogButtonBox.StandardButton.Ok
            | qw.QDialogButtonBox.StandardButton.Cancel
        )

        # Add widgets to layout
        self._layout.addRow(self._col_name_label, self._operator_combo)
        self._layout.addRow(self.app.translate("Value"), self._value_le)
        self._layout.addRow(self._button_box)

        self.setLayout(self._layout)

        # Connect signals
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

    def get_filter(self):
        operator = self._operator_combo.currentData()
        value = self._value_le.text()
        if self.col_info["type"] in ("VARCHAR", "TEXT"):
            value = f"'{value}'"
        else:
            # Neutralize user defined value, make sure it won't execute any code
            try:
                value = str(int(value))
            except ValueError:
                try:
                    value = str(float(value))
                except ValueError:
                    value = f"'{value}'"

        return f'"{self.col_info["name"]}" {operator} {value}'
