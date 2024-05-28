#!/usr/bin/env python


import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from query import Query


class PageSelector(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.rows_label = qw.QLabel("Rows per page")
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
        self.page_label = qw.QLabel("Page")
        self.page_lineedit = qw.QLineEdit()
        self.page_lineedit.setFixedWidth(50)
        self.page_lineedit.setText("1")
        self.page_lineedit.setValidator(qg.QIntValidator(1, 1))
        self.page_lineedit.textChanged.connect(self.set_page)
        self.page_count_label = qw.QLabel("out of (unknown)")
        self.next_button = qw.QPushButton(">")
        self.next_button.clicked.connect(self.goto_next_page)
        self.last_page_button = qw.QPushButton(">>")
        self.last_page_button.clicked.connect(self.goto_last_page)

        self.query = query

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
        self.query.first_page()

    def goto_previous_page(self):
        self.query.previous_page()

    def goto_next_page(self):
        self.query.next_page()

    def goto_last_page(self):
        self.query.last_page()

    def update_page_selector(self):
        # Block signals to avoid infinite loops
        self.page_lineedit.blockSignals(True)
        self.rows_lineedit.blockSignals(True)

        self.rows_lineedit.setText(str(self.query.get_limit()))
        self.page_lineedit.setText(str(self.query.get_page()))

        self.page_lineedit.setValidator(
            qg.QIntValidator(1, self.query.get_page_count())
        )
        self.page_count_label.setText(f"out of {self.query.get_page_count()}")

        self.page_lineedit.blockSignals(False)
        self.rows_lineedit.blockSignals(False)

    def set_page(self, page):
        self.query.set_page(int(page) if page else 1)

    def set_rows_per_page(self, rows_per_page):
        self.query.set_limit(int(rows_per_page or 10))
