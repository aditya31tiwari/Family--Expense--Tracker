# backend.py
"""
SQLite-backed persistence layer for Family Expense Tracker.

Provides a Backend class with methods that match the in-memory FamilyExpenseTracker API,
so main.py can be adapted to call Backend instead of keeping everything in memory.
"""
import sqlite3
import os
from contextlib import closing
from datetime import date, datetime
import csv
import io
from typing import List, Dict, Optional, Tuple

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "expenses.db")


def _ensure_data_dir():
    os.makedirs(DB_DIR, exist_ok=True)


def _connect():
    _ensure_data_dir()
    # detect_types not strictly necessary here, keep plain strings for dates
    return sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)


def init_db():
    """Create tables if they don't exist."""
    with closing(_connect()) as conn:
        c = conn.cursor()
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            earning_status INTEGER DEFAULT 0,
            earnings REAL DEFAULT 0.0
        )
        """
        )
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
        )
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value REAL NOT NULL,
            category TEXT,
            description TEXT,
            date TEXT NOT NULL,
            frequency TEXT DEFAULT 'One-time',
            paid_by TEXT
        )
        """
        )
        conn.commit()


def seed_demo():
    """Insert a few demo members/categories/transactions if DB is empty."""
    init_db()
    with closing(_connect()) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM members")
        members_count = c.fetchone()[0]
        if members_count == 0:
            # seed members
            c.execute("INSERT INTO members (name, earning_status, earnings) VALUES (?, ?, ?)", ("Anish", 1, 15000))
            c.execute("INSERT INTO members (name, earning_status, earnings) VALUES (?, ?, ?)", ("Elina", 1, 20000))
            # seed categories (not strictly needed since categories are stored as free-text)
            c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", ("Groceries",))
            c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", ("Bills",))
            # seed transactions (date as ISO string)
            today = date.today().isoformat()
            c.execute(
                "INSERT INTO transactions (value, category, description, date, frequency, paid_by) VALUES (?, ?, ?, ?, ?, ?)",
                (600.0, "Groceries", "Weekly groceries", today, "One-time", "Elina"),
            )
            c.execute(
                "INSERT INTO transactions (value, category, description, date, frequency, paid_by) VALUES (?, ?, ?, ?, ?, ?)",
                (1200.0, "Bills", "Electricity", today, "One-time", "Anish"),
            )
            conn.commit()


class Backend:
    """
    Simple Backend class exposing methods similar to FamilyExpenseTracker.
    Backend stores members and transactions in SQLite.
    """

    def __init__(self, auto_init: bool = True, auto_seed: bool = False):
        if auto_init:
            init_db()
        if auto_seed:
            seed_demo()

    # ----------------- Members -----------------
    def add_family_member(self, name: str, earning_status: bool = True, earnings: float = 0.0) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Name cannot be empty")
        with closing(_connect()) as conn:
            c = conn.cursor()
            # insert or ignore to avoid duplicate unique names
            c.execute(
                "INSERT OR REPLACE INTO members (name, earning_status, earnings) VALUES (?, ?, ?)",
                (name, int(bool(earning_status)), float(earnings)),
            )
            conn.commit()
            # fetch id
            c.execute("SELECT id FROM members WHERE name = ?", (name,))
            row = c.fetchone()
            return row[0] if row else -1

    def get_members(self) -> List[Dict]:
        with closing(_connect()) as conn:
            c = conn.cursor()
            c.execute("SELECT id, name, earning_status, earnings FROM members ORDER BY name")
            rows = c.fetchall()
            return [
                {"id": r[0], "name": r[1], "earning_status": bool(r[2]), "earnings": float(r[3] or 0.0)}
                for r in rows
            ]

    def delete_family_member(self, member_id: int) -> bool:
        with closing(_connect()) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM members WHERE id = ?", (member_id,))
            conn.commit()
            return c.rowcount > 0

    def update_family_member(self, member_id: int, earning_status: bool = True, earnings: float = 0.0) -> bool:
        with closing(_connect()) as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE members SET earning_status = ?, earnings = ? WHERE id = ?",
                (int(bool(earning_status)), float(earnings), member_id),
            )
            conn.commit()
            return c.rowcount > 0

    def calculate_total_earnings(self) -> float:
        with closing(_connect()) as conn:
            c = conn.cursor()
            c.execute("SELECT SUM(earnings) FROM members WHERE earning_status = 1")
            row = c.fetchone()
            return float(row[0] or 0.0)

    # ----------------- Transactions / Log -----------------
    def add_expense(
        self,
        value: float,
        category: str,
        description: str,
        date_obj_or_str,
        frequency: str = "One-time",
        paid_by: Optional[str] = None,
    ) -> int:
        if value == 0 or value is None:
            raise ValueError("Value cannot be zero")
        if not category or not str(category).strip():
            raise ValueError("Please choose a category")
        # accept date objects or strings (store as ISO)
        if isinstance(date_obj_or_str, (date, datetime)):
            date_str = date_obj_or_str.date().isoformat() if isinstance(date_obj_or_str, datetime) else date_obj_or_str.isoformat()
        else:
            # attempt to accept dd-mm-yyyy or dd/mm/yyyy by trying known formats, else assume it's ISO already
            date_str = str(date_obj_or_str)
            for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
                try:
                    parsed = datetime.strptime(date_str, fmt).date()
                    date_str = parsed.isoformat()
                    break
                except Exception:
                    pass

        with closing(_connect()) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO transactions (value, category, description, date, frequency, paid_by) VALUES (?, ?, ?, ?, ?, ?)",
                (float(value), str(category), str(description or ""), date_str, str(frequency or "One-time"), str(paid_by or "")),
            )
            conn.commit()
            return c.lastrowid

    def get_expense_log(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        Returns raw chronological log entries (most recent first).
        start_date/end_date: ISO date strings 'YYYY-MM-DD' or None.
        """
        q = "SELECT id, value, category, description, date, frequency, paid_by FROM transactions WHERE 1=1"
        params: List = []
        if start_date:
            q += " AND date(date) >= date(?)"
            params.append(start_date)
        if end_date:
            q += " AND date(date) <= date(?)"
            params.append(end_date)
        q += " ORDER BY date(date) DESC, id DESC"
        with closing(_connect()) as conn:
            c = conn.cursor()
            c.execute(q, params)
            rows = c.fetchall()
            return [
                {
                    "id": r[0],
                    "value": float(r[1]),
                    "category": r[2],
                    "description": r[3],
                    "date": r[4],
                    "frequency": r[5],
                    "paid_by": r[6],
                }
                for r in rows
            ]

    def get_aggregated_expenses(self) -> List[Dict]:
        """
        Returns aggregated list grouped by category (mirrors expense_list in-memory).
        Each item: {'category': str, 'value': float, 'description': str (latest), 'frequency': 'One-time' or mix}
        """
        with closing(_connect()) as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT category, SUM(value) as total, GROUP_CONCAT(description, ' ||| ') as descriptions
                FROM transactions
                GROUP BY category
                ORDER BY total DESC
                """
            )
            rows = c.fetchall()
            result = []
            for r in rows:
                cat = r[0] or "Miscellaneous"
                total = float(r[1] or 0.0)
                descriptions = r[2] or ""
                # pick the last description from the concatenated string as a simple heuristic
                last_desc = descriptions.split(" ||| ")[-1] if descriptions else ""
                result.append({"category": cat, "value": total, "description": last_desc})
            return result

    def delete_expense(self, category: str) -> int:
        """
        Deletes aggregated entry by category (mirrors remove in aggregated view).
        This will remove ALL transactions of that category.
        Returns number of rows deleted.
        """
        with closing(_connect()) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM transactions WHERE category = ?", (category,))
            conn.commit()
            return c.rowcount

    def delete_log_entry(self, txn_id: int) -> bool:
        with closing(_connect()) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
            conn.commit()
            return c.rowcount > 0

    def calculate_total_expenditure(self) -> float:
        with closing(_connect()) as conn:
            c = conn.cursor()
            c.execute("SELECT SUM(value) FROM transactions")
            row = c.fetchone()
            return float(row[0] or 0.0)

    # ----------------- Utilities -----------------
    def export_csv(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> bytes:
        """
        Export the transaction log as CSV and return bytes (utf-8).
        The app can use this to power Streamlit's download button.
        """
        rows = self.get_expense_log(start_date=start_date, end_date=end_date)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Paid By", "Category", "Description", "Value", "Frequency"])
        for r in rows:
            writer.writerow([r["date"], r["paid_by"], r["category"], r["description"], r["value"], r["frequency"]])
        return output.getvalue().encode("utf-8")

    def close(self):
        """Placeholder for interface parity; sqlite connections are per-call here."""
        pass
