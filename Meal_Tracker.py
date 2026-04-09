# ====================================
#   IMPORTS
# ====================================
from datetime import datetime                      # Handles current date/time for meal logging
import json                                        # Saves and loads data in lightweight file format
import os                                          # Checks if save file exists before loading
import sys                                         # Lets PySide6 access system-level arguments

from PySide6.QtWidgets import (                    # GUI widgets and layouts from PySide6
    QLabel, QApplication, QWidget, QSizePolicy,
    QLineEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea
)
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt


# ====================================
#   GLOBAL DATA STORAGE
# ====================================
all_meals = []                                     # Stores every meal entry in memory (acts like app database)
date_sections = {}                                 # Maps each date → its collapsible UI container


# ====================================
#   SAVE / LOAD SYSTEM (JSON PERSISTENCE)
# ====================================
DATA_FILE = "yero_data.json"                       # File that permanently stores all logged data

def save_data():
    """Writes all current meals to JSON file so logs persist after closing app."""
    with open(DATA_FILE, "w") as f:                # Opens file in write-mode (overwrites old data)
        json.dump(all_meals, f, indent=4)          # Converts Python list → formatted JSON text


def load_data():
    """Loads JSON file at startup and rebuilds all collapsible sections visually."""
    if not os.path.exists(DATA_FILE):              # Skip if file doesn’t exist yet (first launch)
        return

    with open(DATA_FILE, "r") as f:                # Opens file in read-mode
        data = json.load(f)                        # Loads JSON → list of meal dictionaries

    for meal in data:                              # Rebuilds every saved meal visually
        date = meal["Date"]                        # Reads which date this meal belongs to

        if date not in date_sections:              # If date section missing, create one
            outer_layout, container_layout = create_collapsible_section(date)
            scroll_layout.insertLayout(0, outer_layout)  # Adds section to top of logs page
            date_sections[date] = container_layout       # Stores section for future reference

        meal_widget = create_meal_row(meal)        # Creates label row for each saved meal
        date_sections[date].insertWidget(0, meal_widget)

    all_meals.extend(data)                         # Keeps all loaded data in RAM for updates

    # Recalculates totals for each date after everything is loaded
    for meal in data:
        update_section_totals(meal["Date"])


# ====================================
#   APP + WINDOW SETUP
# ====================================
app = QApplication(sys.argv)                       # Initializes PySide6 event loop (required)
window = QWidget()                                 # Main container for all layouts/widgets
window.setWindowTitle("YeroTracker")               # Title bar text
window.setStyleSheet("background-color: #1C1C1C;") # Global dark-theme background


# ====================================
#   CUSTOM BUTTON CLASS (BOUNCY EFFECT)
# ====================================
class BouncyButton(QPushButton):
    """Extends QPushButton with a smooth bounce animation on click."""
    def mousePressEvent(self, event):
        super().mousePressEvent(event)             # Keeps default click behavior
        self.animate_bounce()                      # Adds bounce afterward

    def animate_bounce(self):
        anim = QPropertyAnimation(self, b"geometry")     # Animates button geometry (position/size)
        anim.setDuration(120)                           # Fast 0.12-second animation
        anim.setEasingCurve(QEasingCurve.OutBounce)     # Gives elastic “pop” feel
        rect = self.geometry()                          # Stores button’s current shape
        anim.setStartValue(rect)
        anim.setKeyValueAt(0.5, rect.adjusted(10, 10, -10, -10))  # Slightly shrinks halfway
        anim.setEndValue(rect)                          # Returns to normal size
        anim.start()
        self._anim = anim                               # Keeps animation alive until finished


# ====================================
#   CORE FUNCTIONS (LOGIC)
# ====================================

def clear():
    """Clears all input fields on main page."""
    meal_entry.clear()
    cal_entry.clear()
    protein_entry.clear()


def delete_meal(widget, meal_data):
    """Removes a meal both visually and from JSON memory."""
    widget.setParent(None)                              # Deletes meal row from UI
    if meal_data in all_meals:
        all_meals.remove(meal_data)                     # Removes from memory list
        save_data()                                     # Updates file immediately
        update_section_totals(meal_data["Date"])        # Refreshes totals for that date


def submit():
    """Adds new meal entry to today’s section and saves it."""
    today = datetime.now().strftime("%m/%d/%Y")         # Gets current date in readable format

    meal_data = {                                       # Bundle user input into dictionary
        "Meal": meal_entry.text(),
        "Calories": cal_entry.text(),
        "Protein": protein_entry.text(),
        "Date": today
    }

    all_meals.append(meal_data)                         # Stores new entry in memory
    save_data()                                         # Saves to JSON file

    # If today’s section doesn’t exist yet, create one dynamically
    if today not in date_sections:
        outer_layout, container_layout = create_collapsible_section(today)
        scroll_layout.insertLayout(0, outer_layout)
        date_sections[today] = container_layout

    # Builds the new meal row visually inside that section
    meal_widget = create_meal_row(meal_data)
    date_sections[today].insertWidget(0, meal_widget)

    update_section_totals(today)                        # Updates total calories/protein count
    clear()                                             # Resets text fields after adding

# ====================================
#   COLLAPSIBLE SECTION BUILDER (PER DATE)
# ====================================
def create_collapsible_section(date_text):
    """Builds collapsible log section for a specific date."""

    # ---------- HEADER (Date + Arrow) ----------
    header_layout = QHBoxLayout()
    header_layout.setContentsMargins(0, 0, 0, 0)

    arrow_label = QLabel("►")                                      # Arrow points right (collapsed)
    arrow_label.setStyleSheet("""
        color: #C83F49;
        font-size: 18px;
        font-weight: bold;
    """)

    # Displays date + total summary (updated dynamically)
    header_label = QLabel(f"{date_text} — 0 kcal / 0g protein")
    header_label.setStyleSheet("""
        color: #C83F49;
        font-size: 20px;
        font-weight: bold;
        margin-top: 10px;
        margin-bottom: 6px;
    """)

    header_layout.addWidget(arrow_label)
    header_layout.addWidget(header_label)
    header_layout.addStretch()

    header_widget = QWidget()
    header_widget.setLayout(header_layout)
    header_widget.header_label = header_label                     # Attach for later updates

    # ---------- CONTAINER (Meal Rows) ----------
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setSpacing(6)
    container_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
    container.setVisible(False)
    container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
    container.setMaximumHeight(0)                                        # Collapsed by default

    # ---------- TOGGLE ANIMATION ----------
    def toggle_visibility():
        is_visible = container.isVisible()
        container.setVisible(not is_visible)
        arrow_label.setText("▼" if not is_visible else "►")              # Arrow flips direction
        container.setMaximumHeight(16777215 if not is_visible else 0)

    header_widget.mousePressEvent = lambda event: toggle_visibility()

    # ---------- COMBINE BOTH ----------
    outer_layout = QVBoxLayout()
    outer_layout.addWidget(header_widget)
    outer_layout.addWidget(container)
    outer_layout.setContentsMargins(0, 2, 0, 2)
    outer_layout.setSpacing(1)
    outer_layout.setAlignment(Qt.AlignTop)

    return outer_layout, container_layout


# ====================================
#   SECTION TOTALS (CALORIES + PROTEIN)
# ====================================
def update_section_totals(date_text):
    """Recalculates daily totals for calories and protein."""
    total_calories = 0
    total_protein = 0

    for meal in all_meals:                                        # Iterate through all logged meals
        if meal["Date"] == date_text:
            try:
                total_calories += float(meal["Calories"])
                total_protein += float(meal["Protein"])
            except ValueError:                                    # Skips invalid numeric values
                pass

    # Find the correct header and update its label text
    for i in range(scroll_layout.count()):
        layout_item = scroll_layout.itemAt(i)
        if not layout_item:
            continue
        layout = layout_item.layout()
        if not layout:
            continue
        header_widget = layout.itemAt(0).widget()
        if hasattr(header_widget, "header_label"):
            label = header_widget.header_label
            if date_text in label.text():
                label.setText(f"{date_text} — {int(total_calories)} kcal / {int(total_protein)}g protein")
                break


# ====================================
#   MEAL ROW BUILDER (LABEL + DELETE)
# ====================================
def create_meal_row(meal_data):
    """Creates a single meal row with name, calories, protein, and delete button."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    # Meal display text (clean box style)
    meal_label = QLabel(f"• {meal_data['Meal']} | {meal_data['Calories']} cal | {meal_data['Protein']}g protein")
    meal_label.setStyleSheet("""
        color: white;
        font-size: 16px;
        background-color: #3A3A3A;
        border-radius: 8px;
        padding: 6px;
    """)

    # Delete button (trash icon)
    delete_button = BouncyButton("🗑️")
    delete_button.setFixedSize(35, 35)
    delete_button.setStyleSheet("""
        background-color: #C83F49;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 14px;
    """)
    delete_button.clicked.connect(lambda: delete_meal(container, meal_data))

    layout.addWidget(meal_label)
    layout.addStretch()
    layout.addWidget(delete_button)
    return container


# ====================================
#   VIEW / CLOSE BUTTON HANDLERS
# ====================================
def view_logs():                        # Shows logs page (right side)
    main_widget.hide()
    logs_widget.show()

def X_button():                         # Closes logs page → back to main
    logs_widget.hide()
    main_widget.show()


# ====================================
#   MAIN PAGE (USER ENTRY SIDE)
# ====================================

# ---------- Entry Fields ----------
meal_entry = QLineEdit()                                 # Meal name input
meal_entry.setFixedSize(300, 50)
meal_entry.setAlignment(Qt.AlignLeft)

cal_entry = QLineEdit()                                  # Calories input
cal_entry.setFixedSize(300, 50)
cal_entry.setAlignment(Qt.AlignLeft)

protein_entry = QLineEdit()                              # Protein input
protein_entry.setFixedSize(300, 50)
protein_entry.setAlignment(Qt.AlignLeft)

# ---------- Labels + Title ----------
meal_label = QLabel("Meal Title")
cal_label = QLabel("Calories")
protein_label = QLabel("Protein (g)")

title = QLabel("YeroTracker - Today's Log")
title.setAlignment(Qt.AlignCenter)
title.setStyleSheet("""
    color: #C83F49;
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 10px;
""")

# ---------- Buttons ----------
subButton = BouncyButton("Submit")
clearButton = BouncyButton("Clear")
viewButton = BouncyButton("View Logs")

buttons = [subButton, clearButton, viewButton]
for btn in buttons:
    btn.setFixedSize(150, 50)
    btn.setStyleSheet("""
        background-color: #C83F49;
        color: white;
        border: none;
        font-size: 16px;
        border-radius: 20px;
        padding: 15px;
    """)

# ---------- Input Styling ----------
for entry in [meal_entry, cal_entry, protein_entry]:
    entry.setStyleSheet("""
        background-color: #2A2A2A;
        color: white;
        border-radius: 10px;
        border: 1px solid #C83F49;
        font-size: 18px;
        padding: 10px;
    """)

for label in [meal_label, cal_label, protein_label]:
    label.setStyleSheet("""
        color: white;
        font-size: 16px;
        padding-left: 10px;
    """)

# ---------- Page Layout ----------
main_layout = QVBoxLayout()
main_layout.setAlignment(Qt.AlignTop)
main_layout.setSpacing(25)

rows = [
    [title],
    [meal_label],
    [meal_entry],
    [cal_label],
    [cal_entry],
    [protein_label],
    [protein_entry],
    [subButton, clearButton, viewButton]
]

for widgets in rows:
    row = QHBoxLayout()
    for w in widgets:
        row.addWidget(w)
    row.setAlignment(Qt.AlignHCenter)
    main_layout.addLayout(row)


# ====================================
#   LOGS PAGE (ALL ENTRIES)
# ====================================

log_title = QLabel("All Past Logs")
log_title.setAlignment(Qt.AlignCenter)
log_title.setStyleSheet("""
    color: #C83F49;
    font-size: 24px;
    font-weight: 600;
    margin-bottom: 4px;
""")

Xbutton = BouncyButton("ⓧ")                          # Close (exit logs)
Xbutton.setFixedSize(30, 30)
Xbutton.setStyleSheet("""
    background-color: #C83F49;
    color: white;
    border: none;
    font-size: 25px;
    border-radius: 15px;
""")

log_header = QHBoxLayout()                            # Header = title + X button
log_header.addWidget(log_title)
log_header.addWidget(Xbutton, alignment=Qt.AlignRight)

# Scrollable container for all date sections
scroll_area = QScrollArea()
scroll_area.setWidgetResizable(True)
scroll_area.setStyleSheet("""
    background-color: #2A2A2A;
    border: 1px solid #C83F49;
    border-radius: 10px;
""")

scroll_content = QWidget()
scroll_layout = QVBoxLayout()
scroll_layout.setSpacing(2)
scroll_layout.setAlignment(Qt.AlignTop)
scroll_content.setLayout(scroll_layout)
scroll_area.setWidget(scroll_content)

# Combine logs title + scroll view
logs_layout = QVBoxLayout()
logs_layout.setSpacing(25)
logs_layout.addLayout(log_header)
logs_layout.addWidget(scroll_area)


# ====================================
#   FINAL WINDOW ASSEMBLY
# ====================================
main_widget = QWidget()
main_widget.setLayout(main_layout)

logs_widget = QWidget()
logs_widget.setLayout(logs_layout)

main_window = QHBoxLayout()                         # Horizontal split (main left, logs right)
main_window.addWidget(main_widget, 1)
main_window.addWidget(logs_widget, 1)
window.setLayout(main_window)

logs_widget.hide()                                  # Hides logs until "View Logs" pressed

# ---------- Button Connections ----------
clearButton.clicked.connect(clear)
subButton.clicked.connect(submit)
viewButton.clicked.connect(view_logs)
Xbutton.clicked.connect(X_button)

# ---------- Load Previous Data ----------
load_data()

# ---------- Run Application ----------
window.show()
sys.exit(app.exec())