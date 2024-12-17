
from datetime import datetime, date
from firebird.driver import connect, driver_config

from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QSpinBox,
                             QComboBox, QPushButton, QCheckBox, QMessageBox,
                             QVBoxLayout, QHBoxLayout, QGridLayout, QDateEdit,
                             QTableWidget, QTableWidgetItem, QGroupBox, QDialog,
                             QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QPalette, QColor

from fpdf import FPDF

# Konfiguracja połączenia z bazą Firebird
driver_config.server_defaults.host.value = 'localhost'
DATABASE = 'hotel.fdb'
USER = 'SYSDBA'
PASSWORD = 'SYSDBA'

def connect_to_db():
    return connect(database=DATABASE, user=USER, password=PASSWORD)

def show_error(msg):
    QMessageBox.critical(None, "Error", msg)

def show_info(msg):
    QMessageBox.information(None, "Info", msg)

def show_warning(msg):
    QMessageBox.warning(None, "Warning", msg)

def show_success(msg):
    QMessageBox.information(None, "Success", msg)


class EditReservationDialog(QDialog):
    def __init__(self, conn, reservation_id, parent=None):
        super(EditReservationDialog, self).__init__(parent)
        self.setWindowTitle("Edit Reservation")
        self.conn = conn
        self.reservation_id = reservation_id

        self.phone_edit = QLineEdit()
        self.check_in_edit = QDateEdit(calendarPopup=True)
        self.check_in_edit.setDisplayFormat("yyyy-MM-dd")
        self.check_out_edit = QDateEdit(calendarPopup=True)
        self.check_out_edit.setDisplayFormat("yyyy-MM-dd")

        form_layout = QFormLayout()
        form_layout.addRow("Phone Number:", self.phone_edit)
        form_layout.addRow("Check-in Date:", self.check_in_edit)
        form_layout.addRow("Check-out Date:", self.check_out_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.save_changes)
        btn_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(btn_box)
        self.setLayout(layout)

        self.load_details()

    def load_details(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT g.PhoneNumber, r.CheckInDate, r.CheckOutDate
                FROM Reservation r
                JOIN Guest g ON r.GuestID = g.ID
                WHERE r.ID = ?
            """, (self.reservation_id,))
            details = cursor.fetchone()
            if not details:
                show_error("Could not retrieve reservation details.")
                self.reject()
                return
    
            self.phone_edit.setText(details[0])
            # Convert date to string before passing to QDate.fromString
            check_in_date_str = details[1].strftime("%Y-%m-%d")
            check_out_date_str = details[2].strftime("%Y-%m-%d")
            
            self.check_in_edit.setDate(QDate.fromString(check_in_date_str, "yyyy-MM-dd"))
            self.check_out_edit.setDate(QDate.fromString(check_out_date_str, "yyyy-MM-dd"))
        except Exception as e:
            show_error(f"Error loading details: {e}")
            self.reject()


    def save_changes(self):
        phone = self.phone_edit.text().strip()
        if not phone:
            show_error("Phone number cannot be empty!")
            return

        check_in_date = self.check_in_edit.date().toPyDate()
        check_out_date = self.check_out_edit.date().toPyDate()

        if check_out_date <= check_in_date:
            show_error("Check-out date must be after check-in date!")
            return

        try:
            cursor = self.conn.cursor()
            # Zaktualizuj dane gościa
            # Najpierw pobierz GuestID
            cursor.execute("SELECT GuestID FROM Reservation WHERE ID = ?", (self.reservation_id,))
            guest_id = cursor.fetchone()
            if not guest_id:
                show_error("Guest not found for reservation.")
                return
            guest_id = guest_id[0]

            cursor.execute("UPDATE Guest SET PhoneNumber = ? WHERE ID = ?", (phone, guest_id))
            # Zaktualizuj daty rezerwacji
            cursor.execute("UPDATE Reservation SET CheckInDate = ?, CheckOutDate = ? WHERE ID = ?",
                           (check_in_date.strftime("%Y-%m-%d"), check_out_date.strftime("%Y-%m-%d"), self.reservation_id))
            self.conn.commit()
            show_success("Reservation updated successfully!")
            self.accept()
        except Exception as e:
            self.conn.rollback()
            show_error(f"Could not update reservation: {e}")


class HotelReservationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hotel Reservation System")
        self.conn = connect_to_db()

        self.bed_count_spin = QSpinBox()
        self.bed_count_spin.setRange(1, 6)

        self.city_combo = QComboBox()
        self.city_combo.addItems(['Los Angeles', 'Manhattan', 'Bydgoszcz', 'Brooklyn'])

        self.check_in_date = QDateEdit(calendarPopup=True)
        self.check_in_date.setDisplayFormat("yyyy-MM-dd")
        
        
        self.check_out_date = QDateEdit(calendarPopup=True)
        self.check_out_date.setDisplayFormat("yyyy-MM-dd")

        self.name_edit = QLineEdit()
        self.last_name_edit = QLineEdit()
        self.phone_edit = QLineEdit()

        self.rooms_table = QTableWidget(0, 2)
        self.rooms_table.setHorizontalHeaderLabels(["Room Number", "Price"])
        self.rooms_table.setSelectionBehavior(self.rooms_table.SelectRows)
        self.rooms_table.setEditTriggers(self.rooms_table.NoEditTriggers)

        # Udogodnienia i usługi
        self.amenity_costs = {'Swimming Pool': 300, 'Fitness Center': 200}
        self.service_costs = {'Cleaning': 100, 'Food Service': 150, 'Housekeeping': 50, 'Birthday Surprise': 400, 'Child Care Taking': 250}

        self.amenities_checkboxes = []
        self.services_checkboxes = []

        for a in self.amenity_costs:
            cb = QCheckBox(a)
            self.amenities_checkboxes.append(cb)

        for s in self.service_costs:
            cb = QCheckBox(s)
            self.services_checkboxes.append(cb)

        self.search_button = QPushButton("Search Rooms")
        self.search_button.clicked.connect(self.search_rooms)
        self.book_button = QPushButton("Book Room")
        self.book_button.clicked.connect(self.book_room)

        self.reservation_table = QTableWidget(0, 6)
        self.reservation_table.setHorizontalHeaderLabels(["ID", "Name", "Last Name", "Room", "Check-In", "Check-Out"])
        self.reservation_table.setSelectionBehavior(self.reservation_table.SelectRows)
        self.reservation_table.setEditTriggers(self.reservation_table.NoEditTriggers)

        self.load_res_button = QPushButton("Load Reservations")
        self.load_res_button.clicked.connect(self.load_reservations)
        self.edit_res_button = QPushButton("Edit Reservation")
        self.edit_res_button.clicked.connect(self.edit_reservation)
        self.cancel_res_button = QPushButton("Cancel Reservation")
        self.cancel_res_button.clicked.connect(self.cancel_reservation)

        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(1, 5)
        self.rating_spin.setValue(5)
        self.rate_city_combo = QComboBox()
        self.rate_city_combo.addItems(['None', 'Los Angeles', 'Manhattan', 'Bydgoszcz', 'Brooklyn'])
        self.rate_building_combo = QComboBox()
        self.rate_building_combo.addItems(['None', 'Building A', 'Building B', 'Building C', 'Building D', 'Building E'])
        self.submit_rating_button = QPushButton("Submit Rating")
        self.submit_rating_button.clicked.connect(self.submit_rating)

        self.init_ui()
        self.apply_modern_style()

    def init_ui(self):
        layout = QVBoxLayout()

        grid = QGridLayout()
        grid.addWidget(QLabel("Number of Beds (1-6):"), 0, 0)
        grid.addWidget(self.bed_count_spin, 0, 1)
        grid.addWidget(QLabel("City:"), 1, 0)
        grid.addWidget(self.city_combo, 1, 1)
        grid.addWidget(QLabel("Check-in Date:"), 2, 0)
        grid.addWidget(self.check_in_date, 2, 1)
        grid.addWidget(QLabel("Check-out Date:"), 3, 0)
        grid.addWidget(self.check_out_date, 3, 1)
        grid.addWidget(self.search_button, 4, 0, 1, 2)
        layout.addLayout(grid)

        layout.addWidget(self.rooms_table)

        guest_grid = QGridLayout()
        guest_grid.addWidget(QLabel("Your Name:"), 0, 0)
        guest_grid.addWidget(self.name_edit, 0, 1)
        guest_grid.addWidget(QLabel("Last Name:"), 1, 0)
        guest_grid.addWidget(self.last_name_edit, 1, 1)
        guest_grid.addWidget(QLabel("Phone Number:"), 2, 0)
        guest_grid.addWidget(self.phone_edit, 2, 1)
        layout.addLayout(guest_grid)

        # Amenities
        amenities_box = QGroupBox("Select Amenities")
        am_layout = QVBoxLayout()
        for cb in self.amenities_checkboxes:
            am_layout.addWidget(cb)
        amenities_box.setLayout(am_layout)
        layout.addWidget(amenities_box)

        # Services
        services_box = QGroupBox("Select Services")
        srv_layout = QVBoxLayout()
        for cb in self.services_checkboxes:
            srv_layout.addWidget(cb)
        services_box.setLayout(srv_layout)
        layout.addWidget(services_box)

        layout.addWidget(self.book_button)

        # Ocena
        rating_grid = QGridLayout()
        rating_grid.addWidget(QLabel("Rate Us:"), 0, 0)
        rating_grid.addWidget(self.rating_spin, 0, 1)
        rating_grid.addWidget(QLabel("City (Optional):"), 1, 0)
        rating_grid.addWidget(self.rate_city_combo, 1, 1)
        rating_grid.addWidget(QLabel("Building (Optional):"), 2, 0)
        rating_grid.addWidget(self.rate_building_combo, 2, 1)
        rating_grid.addWidget(self.submit_rating_button, 3, 0, 1, 2)
        layout.addLayout(rating_grid)

        # Rezerwacje
        layout.addWidget(QLabel("Edit or Cancel Reservations:"))
        layout.addWidget(self.reservation_table)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.load_res_button)
        btn_layout.addWidget(self.edit_res_button)
        btn_layout.addWidget(self.cancel_res_button)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def apply_modern_style(self):
        self.setStyleSheet("QWidget{font-size: 14px;}")
        QApplication.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, Qt.black)
        QApplication.setPalette(palette)

    def search_rooms(self):
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT r.RoomNumber, r.Price FROM Room r
            JOIN Building b ON r.BuildingID = b.ID
            WHERE r.BedCount = ? AND b.City = ? AND r.IsAvailable = 1
            """
            cursor.execute(query, (self.bed_count_spin.value(), self.city_combo.currentText()))
            rooms = cursor.fetchall()
            self.rooms_table.setRowCount(0)
            for room in rooms:
                row_pos = self.rooms_table.rowCount()
                self.rooms_table.insertRow(row_pos)
                self.rooms_table.setItem(row_pos, 0, QTableWidgetItem(str(room[0])))
                self.rooms_table.setItem(row_pos, 1, QTableWidgetItem(str(room[1])))
        except Exception as e:
            show_error(f"Could not fetch rooms: {e}")

    def load_reservations(self):
        phone_number = self.phone_edit.text().strip()
        if not phone_number:
            show_error("Please enter a phone number to load reservations!")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT r.ID, g.Name, g.LastName, ro.RoomNumber, r.CheckInDate, r.CheckOutDate
                FROM Reservation r
                JOIN Guest g ON r.GuestID = g.ID
                JOIN Room ro ON r.RoomID = ro.ID
                WHERE g.PhoneNumber = ?
            """, (phone_number,))
            reservations = cursor.fetchall()
            self.reservation_table.setRowCount(0)
            if not reservations:
                show_info("No reservations found for the provided phone number.")
                return
            for res in reservations:
                row_pos = self.reservation_table.rowCount()
                self.reservation_table.insertRow(row_pos)
                for i, val in enumerate(res):
                    self.reservation_table.setItem(row_pos, i, QTableWidgetItem(str(val)))
        except Exception as e:
            show_error(f"Could not load reservations: {e}")

    def edit_reservation(self):
        selected_items = self.reservation_table.selectedItems()
        if not selected_items:
            show_warning("Please select a reservation to edit.")
            return
        # zakładamy, że ID jest w pierwszej kolumnie
        reservation_id = int(selected_items[0].text())

        dialog = EditReservationDialog(self.conn, reservation_id, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_reservations()

    def cancel_reservation(self):
        selected_items = self.reservation_table.selectedItems()
        if not selected_items:
            show_warning("Please select a reservation to cancel.")
            return
        reservation_id = selected_items[0].text()

        try:
            cursor = self.conn.cursor()
            # Zakładamy, że kluczem jest ID (Reservation.ID)
            cursor.execute("DELETE FROM Reservation WHERE ID = ?", (reservation_id,))
            self.conn.commit()
            self.load_reservations()
            show_success(f"Reservation {reservation_id} canceled successfully.")
        except Exception as e:
            self.conn.rollback()
            show_error(f"Could not cancel reservation: {e}")

    def book_room(self):
        def check_empty(value, field_name):
            if not value.strip():
                show_error(f"{field_name} cannot be empty!")
                return False
            return True

        if not all([
            check_empty(self.name_edit.text(), "Name"),
            check_empty(self.last_name_edit.text(), "Last Name"),
            check_empty(self.phone_edit.text(), "Phone Number"),
        ]):
            return

        if self.rooms_table.currentRow() < 0:
            show_error("Please select a room!")
            return

        check_in_date = self.check_in_date.date().toPyDate()
        check_out_date = self.check_out_date.date().toPyDate()

        if check_out_date <= check_in_date:
            show_error("Check-out date must be after check-in date!")
            return

        try:
            room_number = int(self.rooms_table.item(self.rooms_table.currentRow(), 0).text())
            room_price = float(self.rooms_table.item(self.rooms_table.currentRow(), 1).text())

            cursor = self.conn.cursor()

            # Dodanie gościa
            cursor.execute("""
                INSERT INTO Guest (Name, LastName, PhoneNumber)
                VALUES (?, ?, ?)
                RETURNING ID
            """, (self.name_edit.text().strip(), self.last_name_edit.text().strip(), self.phone_edit.text().strip()))
            guest_id = cursor.fetchone()[0]

            # Pobranie ID pokoju
            cursor.execute("SELECT ID FROM Room WHERE RoomNumber = ?", (room_number,))
            room_id = cursor.fetchone()[0]

            # Dodanie rezerwacji
            cursor.execute("""
                INSERT INTO Reservation (GuestID, RoomID, CheckInDate, CheckOutDate)
                VALUES (?, ?, ?, ?)
                RETURNING ID
            """, (guest_id, room_id, check_in_date.strftime("%Y-%m-%d"), check_out_date.strftime("%Y-%m-%d")))
            reservation_id = cursor.fetchone()[0]

            # Dodanie udogodnień
            for cb in self.amenities_checkboxes:
                if cb.isChecked():
                    cursor.execute("""
                        INSERT INTO Amenity (ReservationID, AmenityType, TotalCost)
                        VALUES (?, ?, ?)
                    """, (reservation_id, cb.text(), self.amenity_costs[cb.text()]))

            # Dodanie usług
            for cb in self.services_checkboxes:
                if cb.isChecked():
                    cursor.execute("""
                        INSERT INTO Service (ReservationID, ServiceType, TotalCost)
                        VALUES (?, ?, ?)
                    """, (reservation_id, cb.text(), self.service_costs[cb.text()]))

            # Obliczenie całkowitego kosztu
            days = (check_out_date - check_in_date).days
            amenities_cost = sum(self.amenity_costs[a.text()] for a in self.amenities_checkboxes if a.isChecked())
            services_cost = sum(self.service_costs[s.text()] for s in self.services_checkboxes if s.isChecked())
            total_cost = (room_price * days) + amenities_cost + services_cost

            # Dodanie płatności
            payment_date = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO Payment (ReservationID, AmenitiesCost, ServiceCost, TotalAmount, PaymentDate)
                VALUES (?, ?, ?, ?, ?)
            """, (reservation_id, amenities_cost, services_cost, total_cost, payment_date))

            self.conn.commit()
            show_success(f"Room {room_number} booked successfully!\nTotal Cost: ${total_cost:.2f}\nPayment Date: {payment_date}")

        except Exception as e:
            self.conn.rollback()
            show_error(f"Could not complete booking: {e}")

    def submit_rating(self):
        rating = self.rating_spin.value()
        city = self.rate_city_combo.currentText()
        building = self.rate_building_combo.currentText()

        if city == "None":
            city = None
        if building == "None":
            building = None

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO UserRating (BuildingName, CityName, Rating)
                VALUES (?, ?, ?)
            """, (building, city, rating))
            self.conn.commit()

            city_msg = f"City: {city}" if city else "City: Not specified"
            building_msg = f"Building: {building}" if building else "Building: Not specified"
            show_info(f"Thank you for rating us {rating}/5!\n{city_msg}\n{building_msg}")

        except Exception as e:
            show_error(f"Could not submit rating: {e}")


if __name__ == "__main__":
    import sys
    from raportgui import DatabaseApp

    app = QApplication(sys.argv)

    # Create instances of both windows
    window1 = HotelReservationApp()
    window1.resize(600, 800)
    window1.show()

    window2 = DatabaseApp()
    window2.resize(1000, 800)
    window2.show()

    # Start the event loop
    sys.exit(app.exec_())
