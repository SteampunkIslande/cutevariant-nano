import polars as pl
import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

import app as ap


class ParquetPreviewModel(qc.QAbstractTableModel):
    """Model for displaying parquet file column names and first values."""

    def __init__(self, app: "ap.App", parent=None):
        super().__init__(parent)
        self.app = app
        self._data = []
        self._headers = [
            self.app.translate("Column Name"),
            self.app.translate("First Value"),
        ]

    def load_parquet(self, file_path: str):
        """Load parquet file and extract column names with their first values."""
        try:
            # Read the parquet file
            df = pl.scan_parquet(file_path).head(1).collect()

            # Reset the data
            self.beginResetModel()
            self._data = [
                (col, df[col].to_list()[0] if not df[col].is_empty() else None)
                for col in df.columns
            ]

            self.endResetModel()
            return True

        except Exception as e:
            qw.QMessageBox.warning(
                None,
                self.app.translate("Error Loading Parquet"),
                self.app.translate("Failed to load parquet file:\n{}").format(e),
            )
            return False

    def rowCount(self, parent=qc.QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=qc.QModelIndex()):
        return 2

    def data(self, index, role=qc.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == qc.Qt.ItemDataRole.DisplayRole:
            return self._data[index.row()][index.column()]

        return None

    def headerData(self, section, orientation, role=qc.Qt.ItemDataRole.DisplayRole):
        if role == qc.Qt.ItemDataRole.DisplayRole:
            if orientation == qc.Qt.Orientation.Horizontal:
                return self._headers[section]
            else:
                return str(section + 1)
        return None


class ParquetPreviewWidget(qw.QWidget):
    """Widget to preview parquet file columns and their first values."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ParquetPreviewModel(self)

        self.table_view = qw.QTableView(self)
        self.table_view.setModel(self.model)

        layout = qw.QVBoxLayout(self)
        layout.addWidget(self.table_view)
        self.setLayout(layout)

    def load_parquet_file(self, file_path: str):
        """Load the parquet file into the model."""
        self.model.load_parquet(file_path)
