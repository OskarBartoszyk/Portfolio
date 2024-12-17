import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QComboBox, QLabel,
    QLineEdit, QWidget, QFileDialog, QTableWidget, QTableWidgetItem, QMessageBox, 
    QHBoxLayout, QDialog, QCheckBox, QDialogButtonBox, QMenu, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt
from firebird.driver import connect, driver_config
from fpdf import FPDF
import numpy as np

class ColumnFilterDialog(QDialog):
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Columns")
        layout = QVBoxLayout()
        
        # Create checkboxes for each column
        self.column_checkboxes = {}
        for col in columns:
            checkbox = QCheckBox(col)
            checkbox.setChecked(True)  # Default to checked
            layout.addWidget(checkbox)
            self.column_checkboxes[col] = checkbox
        
        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_selected_columns(self):
        return [col for col, checkbox in self.column_checkboxes.items() if checkbox.isChecked()]

class RangeFilterDialog(QDialog):
    def __init__(self, column_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Filter Range")
        layout = QVBoxLayout()
        
        # Minimum value input
        min_layout = QHBoxLayout()
        min_layout.addWidget(QLabel("Minimum Value:"))
        self.min_input = QLineEdit(str(column_data.min()))
        min_layout.addWidget(self.min_input)
        layout.addLayout(min_layout)
        
        # Maximum value input
        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Maximum Value:"))
        self.max_input = QLineEdit(str(column_data.max()))
        max_layout.addWidget(self.max_input)
        layout.addLayout(max_layout)
        
        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_range(self):
        try:
            min_val = float(self.min_input.text())
            max_val = float(self.max_input.text())
            return min_val, max_val
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values")
            return None

class GroupByDialog(QDialog):
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Group By")
        layout = QVBoxLayout()
        
        # Create radio buttons for each column
        self.button_group = QButtonGroup()
        self.column_buttons = {}
        
        for col in columns:
            radio_button = QRadioButton(col)
            self.button_group.addButton(radio_button)
            layout.addWidget(radio_button)
            self.column_buttons[col] = radio_button
        
        # Add aggregation options
        layout.addWidget(QLabel("Aggregation Method:"))
        self.agg_combo = QComboBox()
        self.agg_combo.addItems([
            "none","count", "mean", "median", "min", "max", "sum"
        ])
        layout.addWidget(self.agg_combo)
        
        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_groupby_info(self):
        # Find selected column
        for col, button in self.column_buttons.items():
            if button.isChecked():
                return col, self.agg_combo.currentText()
        return None, None

class DatabaseApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Database Report Generator")
        self.setGeometry(100, 100, 1000, 800)

        # Database connection
        driver_config.server_defaults.host.value = 'localhost'
        try:
            self.con = connect(database='/opt/firebird/hotel.fdb', user='SYSDBA', password='SYSDBA')
            self.cur = self.con.cursor()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            sys.exit()

        self.tables_dir = 'database_tables'
        os.makedirs(self.tables_dir, exist_ok=True)

        # Store original DataFrame to allow filtering and sorting
        self.original_df = None
        self.current_df = None
        self.current_sort_column = None
        self.current_sort_order = None

        # UI setup
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Top controls
        top_controls = QHBoxLayout()
        
        self.table_selector = QComboBox()
        self.table_selector.addItems(self.get_table_names())
        self.table_selector.currentTextChanged.connect(self.load_table)
        top_controls.addWidget(QLabel("Select Table:"))
        top_controls.addWidget(self.table_selector)

        # Add load button
        load_button = QPushButton("Load Table")
        load_button.clicked.connect(self.load_table)
        top_controls.addWidget(load_button)

        layout.addLayout(top_controls)

        # Table widget
        self.table_widget = QTableWidget()
        self.table_widget.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        layout.addWidget(self.table_widget)

        # Export to PDF button
        export_pdf_button = QPushButton("Export to PDF")
        export_pdf_button.clicked.connect(self.export_to_pdf)
        layout.addWidget(export_pdf_button)

        # Reset filters button
        reset_button = QPushButton("Reset Filters")
        reset_button.clicked.connect(self.reset_filters)
        layout.addWidget(reset_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        plot_button = QPushButton("Plot data")
        plot_button.clicked.connect(self.create_plot)
        layout.addWidget(plot_button)

    def get_table_names(self):
        self.cur.execute("SELECT RDB$RELATION_NAME FROM RDB$RELATIONS WHERE RDB$SYSTEM_FLAG = 0")
        return [table[0].strip() for table in self.cur.fetchall()]

    def load_table(self):
        selected_table = self.table_selector.currentText()
        csv_file = os.path.join(self.tables_dir, f"{selected_table}.csv")
        
        # Export table if CSV doesn't exist
        if not os.path.exists(csv_file):
            self.cur.execute(f"SELECT * FROM {selected_table}")
            rows = self.cur.fetchall()
            columns = [col[0].strip() for col in self.cur.description]
            self.original_df = pd.DataFrame(rows, columns=columns)
            self.original_df.to_csv(csv_file, index=False)
        else:
            self.original_df = pd.read_csv(csv_file)

        self.current_df = self.original_df.copy()
        self.current_sort_column = None
        self.current_sort_order = None
        self.display_table(self.current_df)

    def display_table(self, df):
        self.table_widget.setRowCount(df.shape[0])
        self.table_widget.setColumnCount(df.shape[1])
        self.table_widget.setHorizontalHeaderLabels(df.columns.tolist())

        for i, row in df.iterrows():
            for j, value in enumerate(row):
                self.table_widget.setItem(i, j, QTableWidgetItem(str(value)))

    def export_to_pdf(self):
        if self.current_df is None or self.current_df.empty:
            QMessageBox.warning(self, "Export Error", "No data available to export")
            return

        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setDefaultSuffix("pdf")
        file_dialog.setNameFilters(["PDF Files (*.pdf)"])

        if file_dialog.exec_() == QFileDialog.Accepted:
            pdf_file_path = file_dialog.selectedFiles()[0]

            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            # Add table headers
            pdf.set_fill_color(200, 220, 255)
            for col in self.current_df.columns:
                pdf.cell(40, 10, col, border=1, fill=True, align='C')
            pdf.ln()

            # Add table rows
            for _, row in self.current_df.iterrows():
                for value in row:
                    pdf.cell(40, 10, str(value), border=1)
                pdf.ln()

            try:
                pdf.output(pdf_file_path)
                QMessageBox.information(self, "Success", f"Data successfully exported to {pdf_file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export data: {e}")
                
    def on_header_clicked(self, column_index):
        column = self.current_df.columns[column_index]
        
        # Create a menu of actions
        menu = QMenu(self)
        
        # Sort Action
        sort_asc = menu.addAction("Sort Ascending")
        sort_desc = menu.addAction("Sort Descending")
        
        # Filter Actions
        menu.addSeparator()
        select_columns = menu.addAction("Select Columns")
        
        # Range Filter (only for numeric columns)
        range_filter = None  # Initialize range_filter here
        if np.issubdtype(self.current_df[column].dtype, np.number):
            range_filter = menu.addAction("Filter Range")
        
        # Grouping for all columns
        group_by = menu.addAction("Group By")
        
        # Show menu
        action = menu.exec_(self.table_widget.mapToGlobal(
            self.table_widget.horizontalHeader().pos()
        ))
        
        if action == sort_asc:
            # Sort the dataframe in ascending order by the selected column
            self.current_df = self.current_df.sort_values(by=column, ascending=True)
            self.current_sort_column = column
            self.current_sort_order = 'asc'
            self.display_table(self.current_df)  # Refresh the table with sorted data
            
        elif action == sort_desc:
            # Sort the dataframe in descending order by the selected column
            self.current_df = self.current_df.sort_values(by=column, ascending=False)
            self.current_sort_column = column
            self.current_sort_order = 'desc'
            self.display_table(self.current_df)  # Refresh the table with sorted data
            
        elif action == select_columns:
            # Open column selection dialog
            dialog = ColumnFilterDialog(self.current_df.columns, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_columns = dialog.get_selected_columns()
                self.current_df = self.current_df[selected_columns]
                self.display_table(self.current_df)
                
        elif action == range_filter:  # This will work now because range_filter is always defined
            # Open range filter dialog for numeric columns
            dialog = RangeFilterDialog(self.original_df[column], self)
            if dialog.exec_() == QDialog.Accepted:
                range_values = dialog.get_range()
                if range_values:
                    min_val, max_val = range_values
                    self.current_df = self.original_df[
                        (self.original_df[column] >= min_val) & 
                        (self.original_df[column] <= max_val)
                    ]
                    # Restore previous sorting if applicable
                    if self.current_sort_column:
                        self.current_df = self.current_df.sort_values(
                            by=self.current_sort_column, 
                            ascending=(self.current_sort_order == 'asc')
                        )
                    self.display_table(self.current_df)
                    
        elif action == group_by:
            # Open grouping dialog
            dialog = GroupByDialog(self.current_df.columns, self)
            if dialog.exec_() == QDialog.Accepted:
                group_column, agg_method = dialog.get_groupby_info()
                if group_column:
                    # Perform grouping
                    if agg_method == 'count':
                        grouped_df = self.current_df.groupby(group_column).size().reset_index(name='count')
                    else:
                        # For other aggregation methods, we need to exclude the grouping column
                        numeric_cols = self.current_df.select_dtypes(include=['int64', 'float64']).columns
                        numeric_cols = [col for col in numeric_cols if col != group_column]
                        
                        if not numeric_cols:
                            QMessageBox.warning(self, "Grouping Error", "No numeric columns available for aggregation")
                            return
                        
                        # Perform aggregation
                        if agg_method == 'none':
                            grouped_df = self.current_df.groupby(group_column, as_index=False).apply(lambda x: x)
                            grouped_df.reset_index(drop=True, inplace=True)
                        elif agg_method == 'mean':
                            grouped_df = self.current_df.groupby(group_column)[numeric_cols].mean().reset_index()
                        elif agg_method == 'median':
                            grouped_df = self.current_df.groupby(group_column)[numeric_cols].median().reset_index()
                        elif agg_method == 'min':
                            grouped_df = self.current_df.groupby(group_column)[numeric_cols].min().reset_index()
                        elif agg_method == 'max':
                            grouped_df = self.current_df.groupby(group_column)[numeric_cols].max().reset_index()
                        elif agg_method == 'sum':
                            grouped_df = self.current_df.groupby(group_column)[numeric_cols].sum().reset_index()
                    
                    self.current_df = grouped_df
                    self.display_table(self.current_df)
    
    
    
    def reset_filters(self):
        # Reset to original dataframe
        self.current_df = self.original_df.copy()
        self.current_sort_column = None
        self.current_sort_order = None
        self.display_table(self.current_df)
        
        
    def create_plot(self):
        # Otwórz dialog wyboru kolumn do wykresu
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Columns for Plot")
        layout = QVBoxLayout()
        
        # Wszystkie kolumny dla X
        normal_columns = self.current_df.columns
        
        # Tylko kolumny numeryczne dla Y
        numeric_columns = self.current_df.select_dtypes(include=['int64', 'float64']).columns
        
        # X-axis selection
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X-axis:"))
        x_combo = QComboBox()
        x_combo.addItems(normal_columns)
        x_layout.addWidget(x_combo)
        layout.addLayout(x_layout)
        
        # Y-axis selection
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y-axis:"))
        y_combo = QComboBox()
        y_combo.addItems(numeric_columns)
        y_layout.addWidget(y_combo)
        layout.addLayout(y_layout)
        
        # Wybór rodzaju wykresu
        plot_type_layout = QHBoxLayout()
        plot_type_layout.addWidget(QLabel("Plot Type:"))
        plot_type_combo = QComboBox()
        plot_type_combo.addItems([
            "Line Plot", 
            "Scatter Plot", 
            "Bar Plot"
        ])
        plot_type_layout.addWidget(plot_type_combo)
        layout.addLayout(plot_type_layout)
        
        # Dodaj przyciski OK i Cancel
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        # Pokaż dialog
        if dialog.exec_() == QDialog.Accepted:
            # Pobierz wybrane kolumny
            x_column = x_combo.currentText()
            y_column = y_combo.currentText()
            plot_type = plot_type_combo.currentText()
            
            # Przygotuj wykres
            plt.figure(figsize=(10, 6))
            
            # Różne rodzaje wykresów
            if plot_type == "Line Plot":
                plt.plot(self.current_df[x_column], self.current_df[y_column], marker='o')
            elif plot_type == "Scatter Plot":
                plt.scatter(self.current_df[x_column], self.current_df[y_column])
            elif plot_type == "Bar Plot":
                plt.bar(self.current_df[x_column], self.current_df[y_column])
            
            plt.title(f'{y_column} vs {x_column}')
            plt.xlabel(x_column)
            plt.ylabel(y_column)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.grid(True)
            plt.show()
            
        
if __name__ == "__main__":
    app2 = QApplication(sys.argv)
    window2 = DatabaseApp()
    window2.show()
    sys.exit(app2.exec_())