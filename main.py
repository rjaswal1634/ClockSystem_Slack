import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import requests
import json
import os
import slack
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import tempfile

# File paths
CLOCK_RECORDS_FILE = 'clock_records.txt'
PDF_RECORDS_FILE = 'clock_records.pdf'
EMPLOYEES_FILE = 'employees.txt'  # File to store employee names
ADMIN_PASSWORD_FILE = 'admin_password.txt'  # File to store admin password

# Set default admin password if the file doesn't exist
if not os.path.exists(ADMIN_PASSWORD_FILE):
    with open(ADMIN_PASSWORD_FILE, 'w') as file:
        file.write('admin')


def save_to_file(employee_name, action):
    """ Save the clock-in/clock-out action to a text file. """
    with open(CLOCK_RECORDS_FILE, 'a') as file:
        file.write(
            f"{employee_name} {action} at {datetime.now().strftime('%H:%M %Y-%m-%d')}\n"
        )


def authenticate_employee(employee_name, password):
    """ Check if the provided employee name and password match the stored credentials. """
    if os.path.exists(EMPLOYEES_FILE):
        with open(EMPLOYEES_FILE, 'r') as file:
            for line in file:
                # Skip empty lines or lines that don't match the expected format
                if not line.strip() or ':' not in line:
                    continue

                try:
                    stored_name, stored_password = line.strip().split(':', 1)
                except ValueError:
                    # Handle cases where splitting by ':' does not yield two values
                    continue

                if employee_name == stored_name and password == stored_password:
                    return True
    return False

def record_clock_in(employee_name, password):
    """ Record a clock-in action after verifying the employee's password. """
    if not authenticate_employee(employee_name, password):
        messagebox.showerror("Error", "Invalid password. Please try again.")
        return

    # Check the last record for the employee
    clocked_in = False
    if os.path.exists(employee_name + '.txt'):
        with open(employee_name + '.txt', 'r') as file:
            records = file.readlines()
            # Reverse the records to get the last entry first
            records.reverse()
            for line in records:
                if line.startswith(f"{employee_name} "):
                    # Check if the last record is "Clocked out"
                    if "Clocked out" in line:
                        clocked_in = False
                    else:
                        clocked_in = True
                    break

    if clocked_in:
        messagebox.showinfo("Error", "Employee is already clocked in.")
    else:
        save_to_file(employee_name, "Clocked in")
        messagebox.showinfo("Success", "Clocked in successfully!")



def record_clock_out(employee_name, password):
    """ Record a clock-out action after verifying the employee's password. """
    if not authenticate_employee(employee_name, password):
        messagebox.showerror("Error", "Invalid password. Please try again.")
        return

    clocked_in = False
    last_action = None

    # Read existing records and determine the status
    if os.path.exists(employee_name + '.txt'):
        with open(employee_name + '.txt', 'r') as file:
            records = file.readlines()
            for line in reversed(records):
                if line.startswith(f"{employee_name} "):
                    last_action = line.strip()
                    break

    if last_action is None:
        messagebox.showinfo("Error", "No records found for employee.")
        return

    if "Clocked out" in last_action:
        messagebox.showinfo("Error", "Employee has already clocked out.")
        return

    if "Clocked in" not in last_action:
        messagebox.showinfo("Error", "Employee is not clocked in.")
        return

    # Record the clock-out action
    save_to_file(employee_name, "Clocked out")
    messagebox.showinfo("Success", "Clocked out successfully!")



from datetime import datetime, timedelta

from datetime import datetime


def auto_clock_out():
    """Automatically clock out employees who haven't clocked out by midnight."""
    midnight = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)

    # Get a list of all text files in the current directory
    for file_name in os.listdir():
        if file_name.endswith('.txt'):
            with open(file_name, 'r') as file:
                records = file.readlines()

            updated_records = []
            clocked_out = False
            for line in records:
                parts = line.strip().split(' ')
                if len(parts) >= 4 and parts[0] == "Clock" and parts[1] == "In:":
                    clock_in_time = datetime.strptime(' '.join(parts[2:]), '%Y-%m-%d %H:%M:%S')

                    # Automatically clock out if the record is from today and no clock-out exists
                    if clock_in_time.date() == datetime.now().date():
                        updated_records.append(line)
                        if not clocked_out:
                            updated_records.append(f"Clock Out: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            clocked_out = True
                else:
                    updated_records.append(line)

            # Write back the updated records to the file
            with open(file_name, 'w') as file:
                file.writelines(updated_records)





def generate_pdf(employee_name=None):
    """ Generate a PDF file from the clock records of each employee. """
    c = canvas.Canvas(PDF_RECORDS_FILE, pagesize=letter)
    width, height = letter
    c.drawString(72, height - 72, "Clock Records")

    y = height - 100
    employee_records = []

    # Get records for a specific employee or all employees
    if employee_name:
        file_names = [f"{employee_name}.txt"]
    else:
        # List all .txt files in the directory
        file_names = [f for f in os.listdir() if f.endswith('.txt')]

    for file_name in file_names:
        current_employee = file_name.split('.')[0]
        if os.path.exists(file_name):
            employee_records.append(f"\n\n{current_employee}'s Records\n")
            with open(file_name, 'r') as file:
                for line in file:
                    employee_records.append(line.strip())

    if not employee_records:
        messagebox.showinfo("Error", "No records found to generate PDF.")
        return

    for record in employee_records:
        if y < 72:  # Check if we need a new page
            c.showPage()
            y = height - 72
        c.drawString(72, y, record)
        y -= 14

    c.save()
    messagebox.showinfo("Success", f"PDF generated successfully: {PDF_RECORDS_FILE}")


def load_employee_names():
    """ Load employee names from the file and return a list. """
    if os.path.exists(EMPLOYEES_FILE):
        with open(EMPLOYEES_FILE, 'r') as file:
            return [line.split(':')[0].strip() for line in file if line.strip()]
    return []


def save_employee_names(employee_list):
    """ Save the updated employee list back to the file. """
    with open(EMPLOYEES_FILE, 'w') as file:
        for name in employee_list:
            file.write(f"{name}\n")


def authenticate_admin(password):
    """ Check if the provided password matches the stored admin password. """
    with open(ADMIN_PASSWORD_FILE, 'r') as file:
        return password == file.read().strip()


def update_admin_password(new_password):
    """ Update the admin password in the file. """
    with open(ADMIN_PASSWORD_FILE, 'w') as file:
        file.write(new_password)


def open_admin_panel():
    admin_panel = ctk.CTkToplevel()
    admin_panel.title("Admin Panel")

    # Load employee names for the dropdown
    employee_list = load_employee_names()
    if not employee_list:
        employee_list = ["No Employees Found"]

    def add_employee():
        name = employee_name_entry.get()
        password = employee_password_entry.get()
        if name and password:
            # Check if employee already exists
            existing_employees = load_employee_names()
            employee_dict = {}

            for emp in existing_employees:
                parts = emp.split(':')
                if len(parts) == 2:
                    employee_dict[parts[0]] = parts[1]
                else:
                    # Handle malformed lines (e.g., log a warning)
                    print(f"Warning: Skipping malformed line in employees file: {emp}")

            if name in employee_dict:
                messagebox.showinfo("Error", "Employee already exists.")
                return

            # Save employee name and password to file
            with open(EMPLOYEES_FILE, 'a') as file:
                file.write(f"{name}:{password}\n")

            # Create a new text file for the employee's clock-in/clock-out records
            employee_file_path = f"{name}.txt"
            if not os.path.exists(employee_file_path):
                with open(employee_file_path, 'w') as file:
                    file.write("")

            # Update dropdown menu
            employee_dropdown.configure(values=["All Employees"] + [name for name in employee_dict.keys()] + [name])
            messagebox.showinfo("Success", "Employee added successfully!")
        else:
            messagebox.showinfo("Error", "Please enter a valid employee name and password.")

    def remove_employee():
        selected_employee = remove_employee_dropdown.get()
        if selected_employee != "No Employees Found" and selected_employee != "All Employees":
            admin_password = remove_employee_password_entry.get()
            if authenticate_admin(admin_password):
                # Remove employee from the list
                employee_list.remove(selected_employee)
                save_employee_names(employee_list)

                # Delete the respective employee's text file
                employee_file = f"{selected_employee}.txt"
                if os.path.exists(employee_file):
                    os.remove(employee_file)

                # Update dropdown menu
                remove_employee_dropdown.configure(values=["All Employees"] + employee_list)
                messagebox.showinfo("Success", f"Employee {selected_employee} removed successfully!")
            else:
                messagebox.showerror("Error", "Incorrect admin password.")
        else:
            messagebox.showinfo("Error", "Please select a valid employee to remove.")

    def connect_slack():
        webhook_url = slack_webhook_entry.get()
        # Implement Slack connection
        messagebox.showinfo("Success", "Slack Webhook connected!")
        slack_msg = {'text': 'Hello'}
        requests.post(webhook_url, data=json.dumps(slack_msg))

    def view_records():
        selected_employee = employee_dropdown.get()

        if selected_employee == "All Employees":
            # Combine records from all employee files
            all_records = []
            employee_names = load_employee_names()

            for employee in employee_names:
                file_path = f"{employee}.txt"
                if os.path.exists(file_path):
                    with open(file_path, 'r') as file:
                        all_records.append(f"\n\n{employee}'s Records\n")
                        all_records.extend(file.readlines())

            if all_records:
                # Write all records to a temporary file
                with open('temp_all_records.txt', 'w') as temp_file:
                    temp_file.writelines(all_records)

                # Generate the PDF from the temporary file
                generate_pdf()

                # Upload to Slack
                upload_to_slack(PDF_RECORDS_FILE, 'All Employees')
                messagebox.showinfo("Success",
                                    "Records for all employees have been written to the PDF and sent to Slack.")
            else:
                messagebox.showinfo("Error", "No records found to generate PDF.")

        else:
            # Generate PDF for the selected employee
            generate_pdf(selected_employee)

            # Load environment variables from .env file
            load_dotenv()

            # Slack token and channel ID
            slack_token = os.getenv('SLACK_TOKEN')
            channel_id = 'C07HVT4351A'  # Replace with your channel ID

            client = WebClient(token=slack_token)

            try:
                # Upload the file
                response = client.files_upload_v2(
                    channel=channel_id,
                    file=PDF_RECORDS_FILE,  # Path to your PDF file
                    title='Clock Records',
                    initial_comment=f"Time cards for {selected_employee} are here."
                )
                assert response["file"]  # Confirm the file was uploaded
                messagebox.showinfo("Success",
                                    f"Records for {selected_employee} have been written to the PDF and sent to Slack.")
            except SlackApiError as e:
                if e.response['error'] == 'not_in_channel':
                    # Try to join the channel before uploading the file
                    try:
                        client.conversations_join(channel=channel_id)
                        print(f"Bot joined channel {channel_id}")
                        # Retry file upload after joining the channel
                        response = client.files_upload_v2(
                            channel=channel_id,
                            file=PDF_RECORDS_FILE,
                            title='Clock Records',
                            initial_comment=f"Time cards for {selected_employee} are here."
                        )
                        assert response["file"]  # Confirm the file was uploaded
                        messagebox.showinfo("Success",
                                            f"Records for {selected_employee} have been written to the PDF and sent to Slack.")
                    except SlackApiError as join_error:
                        print(f"Error joining channel: {join_error.response['error']}")
                else:
                    print(f"Error uploading file: {e.response['error']}")

    def upload_to_slack(file_path, employee_name):
        # Load environment variables from .env file
        load_dotenv()

        # Slack token and channel ID
        slack_token = os.getenv('SLACK_TOKEN')
        channel_id = 'C07HVT4351A'  # Replace with your channel ID

        client = WebClient(token=slack_token)

        try:
            # Upload the file
            response = client.files_upload_v2(
                channel=channel_id,
                file=file_path,
                title='Clock Records',
                initial_comment=f'Time cards for {employee_name} are here.')
            assert response["file"]  # Confirm the file was uploaded
        except SlackApiError as e:
            if e.response['error'] == 'not_in_channel':
                # Try to join the channel before uploading the file
                try:
                    client.conversations_join(channel=channel_id)
                    print(f"Bot joined channel {channel_id}")
                    # Retry file upload after joining the channel
                    response = client.files_upload_v2(
                        channel=channel_id,
                        file=file_path,
                        title='Clock Records',
                        initial_comment=
                        f'Time cards for {employee_name} are here.')
                except SlackApiError as join_error:
                    print(
                        f"Error joining channel: {join_error.response['error']}"
                    )
            else:
                print(f"Error uploading file: {e.response['error']}")

    def change_password():
        new_password = new_password_entry.get()
        if new_password:
            update_admin_password(new_password)
            messagebox.showinfo("Success",
                                "Admin password changed successfully!")
        else:
            messagebox.showinfo("Error", "Please enter a new password.")

    def overwrite_employee_password():
        """ Allow the admin to overwrite an employee's password. """
        selected_employee = employee_dropdown.get()
        new_password = new_password_entry.get()
        admin_password = admin_password_entry.get()

        if not selected_employee or selected_employee == "All Employees":
            messagebox.showinfo("Error", "Please select a valid employee.")
            return

        if not new_password:
            messagebox.showinfo("Error", "Please enter a new password.")
            return

        if authenticate_admin(admin_password):
            # Load existing employee names and passwords
            employee_names = load_employee_names()
            updated_employee_list = []
            employee_found = False

            for emp in employee_names:
                emp_name, emp_password = emp.split(':')
                if emp_name == selected_employee:
                    # Update the password for the selected employee
                    updated_employee_list.append(f"{emp_name}:{new_password}\n")
                    employee_found = True
                else:
                    updated_employee_list.append(f"{emp_name}:{emp_password}\n")

            if employee_found:
                # Save updated employee list back to file
                with open(EMPLOYEES_FILE, 'w') as file:
                    file.writelines(updated_employee_list)

                messagebox.showinfo("Success", f"Password for {selected_employee} has been updated successfully!")
            else:
                messagebox.showinfo("Error", "Employee not found.")

        else:
            messagebox.showerror("Error", "Incorrect admin password.")

    def view_hours():
        """ Display clock-in/out records for a selected employee or all employees. """
        selected_employee = employee_dropdown.get()

        if selected_employee == "All Employees":
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as temp_file:
                employee_names = load_employee_names()
                all_records = []

                for emp in employee_names:
                    emp_name, _ = emp.split(':')
                    emp_filename = f"{emp_name}.txt"
                    if os.path.exists(emp_filename):
                        with open(emp_filename, 'r') as file:
                            all_records.append(f"\n\n{emp_name}'s Records:\n")
                            all_records.append(file.read())

                if all_records:
                    temp_file.write("".join(all_records))
                else:
                    temp_file.write("No records found for any employee.")

                temp_filename = temp_file.name

        else:
            emp_filename = f"{selected_employee}.txt"
            if os.path.exists(emp_filename):
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as temp_file:
                    with open(emp_filename, 'r') as file:
                        records = file.read()
                    if records:
                        temp_file.write(records)
                    else:
                        temp_file.write("No records found for the selected employee.")
                    temp_filename = temp_file.name
            else:
                messagebox.showinfo("Error", f"No record file found for {selected_employee}.")
                return

        # Open the temporary file
        os.startfile(temp_filename)  # Opens the file on Windows

        # Optionally, you can clean up the temporary file after it's opened
        # (uncomment if you want the file to be deleted automatically after some time)
        # os.remove(temp_filename)

    ctk.CTkButton(admin_panel, text="View Hours",
                  command=view_hours).grid(row=11,
                                             column=0,
                                             columnspan=2,
                                             padx=10,
                                             pady=5,
                                             sticky="ew")

    ctk.CTkLabel(admin_panel, text="Employee Name:").grid(row=0,
                                                          column=0,
                                                          padx=10,
                                                          pady=5,
                                                          sticky="e")
    employee_name_entry = ctk.CTkEntry(admin_panel)
    employee_name_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    ctk.CTkLabel(admin_panel, text="Employee Password:").grid(row=1,
                                                          column=0,
                                                          padx=10,
                                                          pady=5,
                                                          sticky="e")
    employee_password_entry = ctk.CTkEntry(admin_panel)
    employee_password_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

    ctk.CTkButton(admin_panel, text="Add Employee",
                  command=add_employee).grid(row=2,
                                             column=0,
                                             columnspan=2,
                                             padx=10,
                                             pady=5,
                                             sticky="ew")

    ctk.CTkLabel(admin_panel,
                 text="Select Employee to Remove:").grid(row=3,
                                                         column=0,
                                                         padx=10,
                                                         pady=5,
                                                         sticky="e")
    remove_employee_dropdown = ctk.CTkOptionMenu(admin_panel,
                                                 values=["All Employees"] +
                                                 load_employee_names())
    remove_employee_dropdown.grid(row=3,
                                  column=1,
                                  padx=10,
                                  pady=5,
                                  sticky="ew")

    ctk.CTkLabel(admin_panel, text="Admin Password:").grid(row=4,
                                                           column=0,
                                                           padx=10,
                                                           pady=5,
                                                           sticky="e")
    remove_employee_password_entry = ctk.CTkEntry(admin_panel, show="*")
    remove_employee_password_entry.grid(row=4,
                                        column=1,
                                        padx=10,
                                        pady=5,
                                        sticky="ew")

    ctk.CTkButton(admin_panel, text="Remove Employee",
                  command=remove_employee).grid(row=5,
                                                column=0,
                                                columnspan=2,
                                                padx=10,
                                                pady=5,
                                                sticky="ew")

    ctk.CTkLabel(admin_panel, text="Slack Webhook URL:").grid(row=6,
                                                              column=0,
                                                              padx=10,
                                                              pady=5,
                                                              sticky="e")
    slack_webhook_entry = ctk.CTkEntry(admin_panel)
    slack_webhook_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

    ctk.CTkButton(admin_panel, text="Connect to Slack",
                  command=connect_slack).grid(row=7,
                                              column=0,
                                              columnspan=2,
                                              padx=10,
                                              pady=5,
                                              sticky="ew")

    ctk.CTkLabel(admin_panel, text="Select Employee:").grid(row=8,
                                                            column=0,
                                                            padx=10,
                                                            pady=5,
                                                            sticky="e")
    employee_dropdown = ctk.CTkOptionMenu(admin_panel,
                                          values=["All Employees"] +
                                          load_employee_names())
    employee_dropdown.grid(row=8, column=1, padx=10, pady=5, sticky="ew")

    ctk.CTkButton(admin_panel, text="View Records",
                  command=view_records).grid(row=9,
                                             column=0,
                                             columnspan=2,
                                             padx=10,
                                             pady=5,
                                             sticky="ew")

    ctk.CTkLabel(admin_panel, text="New Admin Password:").grid(row=10,
                                                               column=0,
                                                               padx=10,
                                                               pady=5,
                                                               sticky="e")
    new_password_entry = ctk.CTkEntry(admin_panel, show="*")
    new_password_entry.grid(row=10, column=1, padx=10, pady=5, sticky="ew")

    ctk.CTkButton(admin_panel, text="Change Password",
                  command=change_password).grid(row=11,
                                                column=0,
                                                columnspan=2,
                                                padx=10,
                                                pady=5,
                                                sticky="ew")

    admin_panel.columnconfigure(1, weight=1)

def open_login_window():
    login_window = ctk.CTk()
    login_window.title("Admin Login")

    def login():
        password = password_entry.get()
        if authenticate_admin(password):
            login_window.destroy()
            open_admin_panel()
        else:
            messagebox.showerror("Error",
                                 "Invalid password. Please try again.")

    ctk.CTkLabel(login_window, text="Admin Password:").grid(row=0,
                                                            column=0,
                                                            padx=10,
                                                            pady=5,
                                                            sticky="e")
    password_entry = ctk.CTkEntry(login_window, show="*")
    password_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

    ctk.CTkButton(login_window, text="Login", command=login).grid(row=1,
                                                                  column=0,
                                                                  columnspan=2,
                                                                  padx=10,
                                                                  pady=5,
                                                                  sticky="ew")

    login_window.mainloop()


def open_main_window():
    root = ctk.CTk()
    root.title("Clock In/Out System")

    # Configure rows and columns to be resizable
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)
    root.grid_rowconfigure(2, weight=1)
    root.grid_rowconfigure(3, weight=1)
    root.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(root, text="Employee Name:").grid(row=0,
                                                   column=0,
                                                   padx=10,
                                                   pady=5,
                                                   sticky="e")
    employee_name_entry = ctk.CTkEntry(root)
    employee_name_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

    ctk.CTkLabel(root, text="Password:").grid(row=1,
                                              column=0,
                                              padx=10,
                                              pady=5,
                                              sticky="e")
    password_entry = ctk.CTkEntry(root, show="*")
    password_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

    # Function to handle Clock In
    def handle_clock_in():
        name = employee_name_entry.get()
        password = password_entry.get()
        # Implement clock-in logic, e.g., check password
        record_clock_in(name, password)

    # Function to handle Clock Out
    def handle_clock_out():
        name = employee_name_entry.get()
        password = password_entry.get()
        # Implement clock-out logic, e.g., check password
        record_clock_out(name, password)

    ctk.CTkButton(root, text="Clock In",
                  command=handle_clock_in).grid(row=2,
                                                column=0,
                                                columnspan=2,
                                                padx=10,
                                                pady=5,
                                                sticky="ew")
    ctk.CTkButton(root, text="Clock Out",
                  command=handle_clock_out).grid(row=3,
                                                 column=0,
                                                 columnspan=2,
                                                 padx=10,
                                                 pady=5,
                                                 sticky="ew")
    ctk.CTkButton(root, text="Admin Panel",
                  command=open_login_window).grid(row=4,
                                                  column=0,
                                                  columnspan=2,
                                                  padx=10,
                                                  pady=5,
                                                  sticky="ew")

    root.mainloop()


if __name__ == "__main__":
    open_main_window()
    auto_clock_out()
# Call this function periodically or at the end of the day to automatically clock out employees
