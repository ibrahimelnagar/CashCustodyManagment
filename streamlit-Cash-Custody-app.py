import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# Paths and constants
DB_DIR = "./data"
DB_FILENAME = os.path.join(DB_DIR, "cash_custody.db")
UPLOAD_FOLDER = "./uploads/"
APP_TITLE = "Cash Custody Management System"
logo_path = 'NATGAS.png'  # Ensure this is the correct path to your image
st.image(logo_path, width=100)  # Adjust the width as needed
CREDITS = "Created by Ibrahim Elnagar, Operation Manager | NATGAS"

# Ensure required directories exist
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the database
def init_database():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            balance REAL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            from_account_id INTEGER,
            to_account_id INTEGER,
            file_path TEXT,
            FOREIGN KEY (from_account_id) REFERENCES accounts (id),
            FOREIGN KEY (to_account_id) REFERENCES accounts (id)
        )
    ''')
    conn.commit()
    conn.close()

# Fetch all accounts
def get_accounts():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, balance FROM accounts")
    accounts = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1], "balance": row[2]} for row in accounts]

# Fetch all transactions
def get_transactions():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.id, t.date, t.type, t.description, t.amount,
               a1.name AS from_account, a2.name AS to_account
        FROM transactions t
        LEFT JOIN accounts a1 ON t.from_account_id = a1.id
        LEFT JOIN accounts a2 ON t.to_account_id = a2.id
    ''')
    transactions = cursor.fetchall()
    conn.close()
    return transactions

# Add a new account
def add_account(name, balance):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", (name, balance))
    conn.commit()
    conn.close()

# Add a new transaction
def add_transaction(transaction_data):
    """Add a new transaction and update account balances."""
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()

    # Insert the transaction into the database
    cursor.execute('''
        INSERT INTO transactions (date, type, description, amount, from_account_id, to_account_id, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', transaction_data)

    # Update account balances for transfers and deposits
    transaction_type = transaction_data[1]
    amount = transaction_data[3]
    from_account_id = transaction_data[4]
    to_account_id = transaction_data[5]

    if transaction_type == "DEPOSIT":
        if to_account_id:
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))
        if from_account_id:
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
    elif transaction_type == "TRANSFER":
        if from_account_id:
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
        if to_account_id:
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))
    elif transaction_type == "EXPENSE":
        if from_account_id:
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
        if to_account_id:
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))

    conn.commit()
    conn.close()

# Edit a transaction
def edit_transaction(transaction_id, updated_data):
    """Edit an existing transaction and update account balances."""
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()

    # Fetch the current transaction details
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
    current_transaction = cursor.fetchone()

    if not current_transaction:
        st.error("Transaction not found.")
        return

    current_amount = current_transaction[4]
    current_from_account_id = current_transaction[5]
    current_to_account_id = current_transaction[6]

    new_amount = updated_data[3]
    new_from_account_id = updated_data[4]
    new_to_account_id = updated_data[5]

    # Update the transaction in the database
    cursor.execute('''
        UPDATE transactions
        SET date = ?, type = ?, description = ?, amount = ?, from_account_id = ?, to_account_id = ?, file_path = ?
        WHERE id = ?
    ''', (*updated_data, transaction_id))

    # Adjust account balances
    if current_from_account_id:
        cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (current_amount, current_from_account_id))
    if current_to_account_id:
        cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (current_amount, current_to_account_id))

    if new_from_account_id:
        cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (new_amount, new_from_account_id))
    if new_to_account_id:
        cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (new_amount, new_to_account_id))

    conn.commit()
    conn.close()

# Delete a transaction
def delete_transaction(transaction_id):
    """Delete a transaction and revert account balances."""
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()

    # Fetch the transaction details
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
    transaction = cursor.fetchone()

    if not transaction:
        st.error("Transaction not found.")
        return

    amount = transaction[4]
    from_account_id = transaction[5]
    to_account_id = transaction[6]

    # Delete the transaction from the database
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))

    # Revert account balances
    if from_account_id:
        cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, from_account_id))
    if to_account_id:
        cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, to_account_id))

    conn.commit()
    conn.close()

# Delete an account
def delete_account(account_id):
    """Delete an account if its balance is zero."""
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()

    # Fetch the account details
    cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    account = cursor.fetchone()

    if not account:
        st.error("Account not found.")
        return

    balance = account[2]

    if balance != 0:
        st.error("Cannot delete account with non-zero balance.")
        return

    # Delete the account from the database
    cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))

    conn.commit()
    conn.close()

# Export transactions to Excel
def export_transactions():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.date, t.type, t.description, t.amount,
               a1.name AS from_account, a2.name AS to_account, t.file_path
        FROM transactions t
        LEFT JOIN accounts a1 ON t.from_account_id = a1.id
        LEFT JOIN accounts a2 ON t.to_account_id = a2.id
    ''')
    transactions = cursor.fetchall()
    conn.close()
    df = pd.DataFrame(transactions, columns=[
        "Date", "Type", "Description", "Amount", "From Account", "To Account", "File Path"
    ])
    excel_path = os.path.join(UPLOAD_FOLDER, "transactions.xlsx")
    df.to_excel(excel_path, index=False)
    return excel_path

# Reset the application
def reset_application():
    if st.session_state.get("confirm_reset", False):
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accounts")
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='accounts'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
        conn.commit()
        conn.close()
        st.success("Application reset successfully!")
        st.session_state["confirm_reset"] = False
        # Refresh accounts and transactions dynamically
        with accounts_placeholder.container():
            accounts = get_accounts()
            st.dataframe(pd.DataFrame(accounts))
        with transactions_placeholder.container():
            transactions = get_transactions()
            if transactions:
                df_transactions = pd.DataFrame(transactions, columns=[
                    "ID", "Date", "Type", "Description", "Amount", "From Account", "To Account"
                ])
                st.dataframe(df_transactions)
            else:
                st.write("No transactions available.")
    else:
        st.session_state["confirm_reset"] = st.sidebar.button("Confirm Reset")
        if st.session_state["confirm_reset"]:
            st.warning("Are you sure you want to reset the application? This action cannot be undone.")

# Initialize the database before starting the app
init_database()

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Streamlit UI
st.title(APP_TITLE)
st.sidebar.header("Navigation")
st.markdown(f"### {CREDITS}")

# Enhanced UI Example
st.markdown('<div class="header"><h2>Accounts</h2></div>', unsafe_allow_html=True)
accounts_placeholder = st.empty()
with accounts_placeholder.container():
    accounts = get_accounts()
    st.dataframe(pd.DataFrame(accounts))

st.divider()

st.markdown('<div class="header"><h2>Transactions</h2></div>', unsafe_allow_html=True)
transactions_placeholder = st.empty()
with transactions_placeholder.container():
    transactions = get_transactions()
    if transactions:
        df_transactions = pd.DataFrame(transactions, columns=[
            "ID", "Date", "Type", "Description", "Amount", "From Account", "To Account"
        ])

        # Add sorting functionality to the table headers
        sort_column = st.selectbox("Sort by", ["ID", "Date", "Type", "Description", "Amount", "From Account", "To Account"], key="sort_column")
        sort_ascending = st.checkbox("Sort Ascending", value=True, key="sort_ascending")

        if sort_column:
            df_transactions = df_transactions.sort_values(by=sort_column, ascending=sort_ascending)

        # Display the DataFrame
        st.dataframe(df_transactions)
    else:
        st.write("No transactions available.")

# Create vertical sections in the sidebar using expanders
with st.sidebar.expander("Account Management"):
    st.markdown('<div class="sidebar-section"><h3>Add Account</h3></div>', unsafe_allow_html=True)
    account_name = st.text_input("Account Name")
    account_balance = st.number_input("Initial Balance", min_value=0.0)
    if st.button("Add Account"):
        add_account(account_name, account_balance)
        st.success(f"Account '{account_name}' added successfully!")
        # Refresh accounts dynamically
        with accounts_placeholder.container():
            accounts = get_accounts()
            st.dataframe(pd.DataFrame(accounts))

    st.markdown('<div class="sidebar-section"><h3>Delete Account</h3></div>', unsafe_allow_html=True)
    account_id_to_delete = st.number_input("Account ID to Delete", min_value=1, step=1)
    if st.button("Delete Account"):
        delete_account(account_id_to_delete)
        st.success("Account deleted successfully!")
        # Refresh accounts dynamically
        with accounts_placeholder.container():
            accounts = get_accounts()
            st.dataframe(pd.DataFrame(accounts))

with st.sidebar.expander("Transaction Management"):
    st.markdown('<div class="sidebar-section"><h3>Add Transaction</h3></div>', unsafe_allow_html=True)
    transaction_date = st.date_input("Date")
    transaction_type = st.selectbox("Type", ["DEPOSIT", "EXPENSE", "TRANSFER"])
    transaction_desc = st.text_input("Description")
    transaction_amount = st.number_input("Amount", min_value=0.0)
    from_account = st.selectbox("From Account", [None] + [acc["name"] for acc in accounts])
    to_account = st.selectbox("To Account", [None] + [acc["name"] for acc in accounts])
    uploaded_file = st.file_uploader("Upload File", key="add_transaction_file_uploader")
    if st.button("Add Transaction"):
        file_path = None
        if uploaded_file:
            file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.read())
        from_account_id = next((acc["id"] for acc in accounts if acc["name"] == from_account), None)
        to_account_id = next((acc["id"] for acc in accounts if acc["name"] == to_account), None)
        add_transaction((transaction_date, transaction_type, transaction_desc, transaction_amount, from_account_id, to_account_id, file_path))
        st.success("Transaction added successfully!")
        # Refresh accounts and transactions dynamically
        with accounts_placeholder.container():
            accounts = get_accounts()
            st.dataframe(pd.DataFrame(accounts))
        with transactions_placeholder.container():
            transactions = get_transactions()
            df_transactions = pd.DataFrame(transactions, columns=[
                "ID", "Date", "Type", "Description", "Amount", "From Account", "To Account"
            ])
            sort_column = st.session_state.get("sort_column", "ID")
            sort_ascending = st.session_state.get("sort_ascending", True)
            if sort_column:
                df_transactions = df_transactions.sort_values(by=sort_column, ascending=sort_ascending)
            st.dataframe(df_transactions)

    st.markdown('<div class="sidebar-section"><h3>Edit Transaction</h3></div>', unsafe_allow_html=True)
    transaction_id_to_edit = st.number_input("Transaction ID to Edit", min_value=1, step=1)
    if st.button("Fetch Transaction Details"):
        transaction_to_edit = next((t for t in transactions if t[0] == transaction_id_to_edit), None)
        if transaction_to_edit:
            st.session_state["transaction_to_edit"] = transaction_to_edit
            st.session_state["edit_mode"] = True
        else:
            st.error("Transaction not found.")

    if st.session_state.get("edit_mode"):
        transaction_to_edit = st.session_state["transaction_to_edit"]
        edit_date = st.date_input("Date", value=pd.to_datetime(transaction_to_edit[1]))
        edit_type = st.selectbox("Type", ["DEPOSIT", "EXPENSE", "TRANSFER"], index=["DEPOSIT", "EXPENSE", "TRANSFER"].index(transaction_to_edit[2]))
        edit_desc = st.text_input("Description", value=transaction_to_edit[3])
        edit_amount = st.number_input("Amount", min_value=0.0, value=transaction_to_edit[4])
        account_names = [None] + [acc["name"] for acc in accounts]
        edit_from_account = st.selectbox("From Account", account_names, index=account_names.index(transaction_to_edit[5]))
        edit_to_account = st.selectbox("To Account", account_names, index=account_names.index(transaction_to_edit[6]))
        edit_file_path = st.file_uploader("Upload File", key="edit_transaction_file_uploader")
        if st.button("Update Transaction"):
            file_path = transaction_to_edit[7]
            if edit_file_path:
                file_path = os.path.join(UPLOAD_FOLDER, edit_file_path.name)
                with open(file_path, "wb") as f:
                    f.write(edit_file_path.read())
            from_account_id = next((acc["id"] for acc in accounts if acc["name"] == edit_from_account), None)
            to_account_id = next((acc["id"] for acc in accounts if acc["name"] == edit_to_account), None)
            edit_transaction(transaction_to_edit[0], (edit_date, edit_type, edit_desc, edit_amount, from_account_id, to_account_id, file_path))
            st.success("Transaction updated successfully!")
            st.session_state["edit_mode"] = False
            # Refresh accounts and transactions dynamically
            with accounts_placeholder.container():
                accounts = get_accounts()
                st.dataframe(pd.DataFrame(accounts))
            with transactions_placeholder.container():
                transactions = get_transactions()
                df_transactions = pd.DataFrame(transactions, columns=[
                    "ID", "Date", "Type", "Description", "Amount", "From Account", "To Account"
                ])
                sort_column = st.session_state.get("sort_column", "ID")
                sort_ascending = st.session_state.get("sort_ascending", True)
                if sort_column:
                    df_transactions = df_transactions.sort_values(by=sort_column, ascending=sort_ascending)
                st.dataframe(df_transactions)

    st.markdown('<div class="sidebar-section"><h3>Delete Transaction</h3></div>', unsafe_allow_html=True)
    transaction_id_to_delete = st.number_input("Transaction ID to Delete", min_value=1, step=1)
    if st.button("Delete Transaction"):
        delete_transaction(transaction_id_to_delete)
        st.success("Transaction deleted successfully!")
        # Refresh accounts and transactions dynamically
        with accounts_placeholder.container():
            accounts = get_accounts()
            st.dataframe(pd.DataFrame(accounts))
        with transactions_placeholder.container():
            transactions = get_transactions()
            df_transactions = pd.DataFrame(transactions, columns=[
                "ID", "Date", "Type", "Description", "Amount", "From Account", "To Account"
            ])
            sort_column = st.session_state.get("sort_column", "ID")
            sort_ascending = st.session_state.get("sort_ascending", True)
            if sort_column:
                df_transactions = df_transactions.sort_values(by=sort_column, ascending=sort_ascending)
            st.dataframe(df_transactions)

with st.sidebar.expander("Export and Reset"):
    st.markdown('<div class="sidebar-section"><h3>Export Transactions</h3></div>', unsafe_allow_html=True)
    if st.button("Export Transactions to Excel"):
        excel_path = export_transactions()
        st.download_button(
            label="Download Excel File",
            data=open(excel_path, "rb").read(),
            file_name="transactions.xlsx"
        )

    st.markdown('<div class="sidebar-section"><h3>Reset Application</h3></div>', unsafe_allow_html=True)
    reset_application()