#!/usr/bin/env python


from functools import partial
from typing import List, Union

import duckdb as db
import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from common_widgets.page_selector import PageSelector
from commons import duck_db_literal_string_list
from query import Query
from query_table_model import QueryTableModel


class QueryTableProxyModel(qc.QSortFilterProxyModel):
    # Automatically hides columns which names start with a dot
    def filterAcceptsColumn(self, source_column: int, source_parent: qc.QModelIndex):
        source_model = self.sourceModel()
        header: str = source_model.headerData(
            source_column, qc.Qt.Orientation.Horizontal
        )
        return not header.startswith(".")

    # Rename columns by splitting on every colon
    def headerData(
        self,
        section: int,
        orientation: qc.Qt.Orientation,
        role: int = qc.Qt.ItemDataRole.DisplayRole,
    ):
        source_model = self.sourceModel()
        actual_section = self.mapToSource(self.index(0, section)).column()
        header: str = source_model.headerData(actual_section, orientation, role)
        if role == qc.Qt.ItemDataRole.DisplayRole:
            return header.split(":")[0] if header else header
        return header


def insert_validation_data(
    conn: db.DuckDBPyConnection,
    table_uuid: str,
    validation_hash: int,
    sample_name: str,
    run_name: str,
    transcript_ID: str,
    variant_hash: int,
    accepted: bool,
    comment: str,
    tags: List[str],
    acmg_classification: str,
    distribution_anomalie: str,
):
    is_validation_hash_present = (
        conn.sql(
            f"""SELECT COUNT(*) FROM "{table_uuid}" WHERE validation_hash = {validation_hash}"""
        ).fetchone()[0]
        == 1
    )

    username = qc.QDir().home().dirName()

    if not is_validation_hash_present:
        conn.sql(
            f"""INSERT INTO "{table_uuid}" (validation_hash,sample_name,run_name, transcript_ID, variant_hash) VALUES ({validation_hash}, '{sample_name}', '{run_name}', '{transcript_ID}', {variant_hash})"""
        )

    conn.sql(
        f"""UPDATE "{table_uuid}" SET accepted = {accepted}, comment = comment || [row('{comment}','{username}',NOW())], tags = {duck_db_literal_string_list(tags)}, acmg_classification = '{acmg_classification}', distribution_anomalie = '{distribution_anomalie}' WHERE validation_hash = {validation_hash}"""
    )


class QueryTableWidget(qw.QWidget):

    # Add signal that updates when selected rows change
    selection_changed = qc.Signal()

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self.query = query
        self.model = QueryTableModel(query)
        self.proxy_model = QueryTableProxyModel()
        self.proxy_model.setSourceModel(self.model)

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

        self.page_selector = PageSelector(query)

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
            qc.QCoreApplication.tr("Filtrer cette colonne (simple expression)")
        )
        filter_action.triggered.connect(partial(self.filter_column, index))

        order_action: qg.QAction = menu.addAction(
            qc.QCoreApplication.tr("Trier cette colonne")
        )
        order_action.triggered.connect(partial(self.add_order_by, index))

        menu.exec(self.table_view.mapToGlobal(pos))

    def add_order_by(self, index: qc.QModelIndex):
        self.query.order_by_model.add_order_by(
            self.proxy_model.headerData(index.column(), qc.Qt.Orientation.Horizontal),
            "ASC",
        )

    def show_table_context_menu(self, pos):
        menu = qw.QMenu()

        index = self.table_view.indexAt(pos)

        filter_action: qg.QAction = menu.addAction(
            qc.QCoreApplication.tr(
                "(DEBUG): Voir les données sous-jacentes de cette ligne"
            )
        )
        filter_action.triggered.connect(partial(self.show_row_userdata, index))

        add_variant_action: qg.QAction = menu.addAction(
            qc.QCoreApplication.tr("Ajouter le variant à la validation")
        )
        add_variant_action.triggered.connect(self.add_variant_to_validation)

        goto_mobidetails_action: qg.QAction = menu.addAction(
            qc.QCoreApplication.tr("Voir le variant sur Mobidetails")
        )
        goto_mobidetails_action.triggered.connect(partial(self.goto_mobidetails, index))

        menu.exec(qg.QCursor.pos())

    def add_variant_to_validation(self):
        conn = self.query.datalake.get_database("validation")
        for index in self.table_view.selectionModel().selectedRows():
            row_data: dict[str, Union[str | int]] = index.data(
                qc.Qt.ItemDataRole.UserRole
            )
            validation_hash = row_data[".validation_hash"]
            variant_hash = row_data[".variant_hash"]

            val_table_uuid = self.query.get_editable_table_name()

            insert_validation_data(
                conn,
                val_table_uuid,
                validation_hash,
                row_data["Échantillon"],
                row_data["Nom du run"],
                row_data["NM"],
                variant_hash,
                True,
                "",
                [],
                "",
                "",
            )
        conn.close()
        self.query.commit()

    def show_row_userdata(self, index: qc.QModelIndex):
        row_data = index.data(qc.Qt.ItemDataRole.UserRole)
        dialog = qw.QMessageBox(self)
        dialog.setText(
            "".join(f"<br><b>{k}</b>: {v}</br>" for k, v in row_data.items())
        )
        dialog.setWindowTitle(qc.QCoreApplication.tr("Données sous-jacentes"))
        dialog.exec()

    def export_to_excel(self):
        file_name, _ = qw.QFileDialog.getSaveFileName(
            self,
            qc.QCoreApplication.tr("Exporter la table de validation vers Excel"),
            "",
            qc.QCoreApplication.tr("Fichiers Excel (*.xlsx)"),
        )
        if file_name:
            self.model.export_to_excel(file_name)

    def goto_mobidetails(self, index: qc.QModelIndex):
        import requests

        def mobidetails_get(nc, position, reference, alternate, **kwargs):
            position = int(position)
            base = "https://mobidetails.iurc.montp.inserm.fr/MD/api/variant/exists"
            if len(reference) > len(alternate):
                # Deletion
                print("Deletion")
                q = f"{base}/{nc}:g.{position}_{position+len(reference)-len(alternate)+1}del"
            elif len(reference) < len(alternate):
                # Insertion
                q = f"{base}/{nc}:g.{position}_{position+1}ins{alternate[1:]}"
                print("Insertion")
            else:
                # Substitution
                q = f"{base}/{nc}:g.{position}{reference}>{alternate}"
                print("Substitution")
            res = requests.get(q)
            if res.status_code == 200:
                return res.json()
            return {}

        row_data: dict[str] = index.data(qc.Qt.ItemDataRole.UserRole)
        nc = row_data.get(".NC", None)
        position = row_data.get("Position", None)
        reference = row_data.get("Allèle de référence", None)
        alternate = row_data.get("Allèle alternatif", None)
        if all((nc, position, reference, alternate)):
            res = mobidetails_get(nc, position, reference, alternate)
            if "mobidetails_id" in res:
                qg.QDesktopServices.openUrl(
                    qc.QUrl(
                        f"https://mobidetails.iurc.montp.inserm.fr/MD/api/variant/{res['mobidetails_id']}/browser/"
                    )
                )
            else:
                print(res)
                qw.QMessageBox.warning(
                    self,
                    qc.QCoreApplication.tr("Mobidetails"),
                    qc.QCoreApplication.tr("Variant non trouvé dans Mobidetails"),
                )

    def filter_column(self, index: qc.QModelIndex):

        col_name = index.model().headerData(
            index.column(), qc.Qt.Orientation.Horizontal
        )
        dialog = SimpleFilterDialog(self.query.get_column_info(col_name), self)

        if dialog.exec_() == qw.QDialog.DialogCode.Accepted:
            filter_text = dialog.get_filter()
            self.query.filter_model.add_filter(
                filter_text,
            )


class SimpleFilterDialog(qw.QDialog):

    def __init__(self, col_info: dict, parent=None):
        super().__init__(parent)

        self.col_info = col_info

        self.setWindowTitle(qc.QCoreApplication.tr("Filtrer une colonne"))

        # Create widgets
        # Create a label for the column name
        # Create a combo box for the operator (according to the column type)
        # Create a line edit for the value
        # Create a button box with OK and Cancel buttons

        self._layout = qw.QFormLayout()

        self._col_name_label = qw.QLabel(col_info["name"])
        self._operator_combo = qw.QComboBox()

        operators = [
            ("égale à", "="),
            ("différent de", "!="),
            ("est nul", "IS NULL"),
            ("n'est pas nul", "IS NOT NULL"),
        ]

        if self.col_info["type"] in ("INTEGER", "FLOAT"):
            operators += [
                ("supérieur à", ">"),
                ("supérieur ou égal à", ">="),
                ("inférieur à", "<"),
                ("inférieur ou égal à", "<="),
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
        self._layout.addRow("Valeur", self._value_le)
        self._layout.addRow(self._button_box)

        self.setLayout(self._layout)

        # Connect signals
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

    def get_filter(self):
        operator = self._operator_combo.currentData()
        value = self._value_le.text()
        return f'"{self.col_info["name"]}" {operator} \'{value}\''
