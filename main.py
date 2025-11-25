# main.py
from datetime import datetime, date
from typing import Optional, List
from backend import Backend  # requires backend.py to be present

# ---- Domain classes (compatible with your app.py) ----
class FamilyMember:
    def __init__(self, name: str, earning_status: bool = True, earnings: float = 0.0, id: Optional[int] = None):
        self.id = id
        self.name = name
        self.earning_status = bool(earning_status)
        self.earnings = float(earnings)

    def __str__(self):
        return (
            f"Name: {self.name}, Earning Status: {'Earning' if self.earning_status else 'Not Earning'}, "
            f"Earnings: {self.earnings}"
        )


class Expense:
    def __init__(
        self,
        value: float,
        category: str,
        description: str,
        date_obj_or_str,
        frequency: str = "One-time",
        paid_by: str = "Unknown",
        id: Optional[int] = None,
    ):
        self.id = id
        self.value = float(value)
        self.category = category
        self.description = description
        # Normalize date to datetime.date where possible
        if isinstance(date_obj_or_str, date):
            self.date = date_obj_or_str
        else:
            # try ISO first, then common formats
            d = None
            try:
                d = datetime.fromisoformat(str(date_obj_or_str)).date()
            except Exception:
                for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
                    try:
                        d = datetime.strptime(str(date_obj_or_str), fmt).date()
                        break
                    except Exception:
                        pass
            self.date = d if d else str(date_obj_or_str)
        self.frequency = frequency
        self.paid_by = paid_by

    def __str__(self):
        return (
            f"Value: {self.value}, Category: {self.category}, Description: {self.description}, "
            f"Date: {self.date}, Frequency: {self.frequency}, Paid By: {self.paid_by}"
        )


# ---- FamilyExpenseTracker wrapper that uses Backend internally ----
class FamilyExpenseTracker:
    def __init__(self, auto_seed: bool = False):
        """
        auto_seed: if True and DB empty, seed demo data.
        """
        # backend provides persistent storage
        self._backend = Backend(auto_init=True, auto_seed=auto_seed)
        # in-memory views used by your app.py (keeps the same interface)
        self.members: List[FamilyMember] = []
        self.expense_list: List[Expense] = []  # aggregated by category
        self.expense_log: List[Expense] = []  # raw chronological log
        # load from DB
        self.refresh()

    # -------- internal sync --------
    def refresh(self):
        """Reload members, aggregated expense list, and expense log from DB."""
        # members
        self.members = []
        for m in self._backend.get_members():
            fm = FamilyMember(name=m["name"], earning_status=m["earning_status"], earnings=m["earnings"], id=m["id"])
            self.members.append(fm)

        # aggregated expenses (grouped by category)
        self.expense_list = []
        for a in self._backend.get_aggregated_expenses():
            # aggregated entries won't have DB id (they are groups)
            exp = Expense(value=a["value"], category=a["category"], description=a.get("description", ""), date_obj_or_str=date.today(), frequency="One-time", paid_by="Unknown", id=None)
            # Use the aggregated description as stored
            self.expense_list.append(exp)

        # raw chronological log
        self.expense_log = []
        for r in self._backend.get_expense_log():
            # r has keys: id, value, category, description, date, frequency, paid_by
            # convert r['date'] ISO string to date object if possible
            dt = r["date"]
            d_obj = None
            try:
                d_obj = datetime.fromisoformat(dt).date()
            except Exception:
                try:
                    d_obj = datetime.strptime(dt, "%d-%m-%Y").date()
                except Exception:
                    d_obj = dt  # keep original string
            e = Expense(value=r["value"], category=r["category"], description=r["description"], date_obj_or_str=d_obj, frequency=r.get("frequency", "One-time"), paid_by=r.get("paid_by", "Unknown"), id=r["id"])
            self.expense_log.append(e)

    # -------- Members API (keeps same method names) --------
    def add_family_member(self, name: str, earning_status: bool = True, earnings: float = 0.0):
        if not str(name).strip():
            raise ValueError("Name field cannot be empty")
        # backend returns id (or -1 if something odd)
        _id = self._backend.add_family_member(name.strip(), earning_status, earnings)
        self.refresh()
        return _id

    def delete_family_member(self, member):
        # accept either FamilyMember instance or id
        member_id = getattr(member, "id", None) or member
        if member_id is None:
            # try lookup by name
            if hasattr(member, "name"):
                candidates = [m for m in self.members if m.name == member.name]
                if candidates:
                    member_id = candidates[0].id
        if member_id is None:
            return False
        ok = self._backend.delete_family_member(member_id)
        self.refresh()
        return ok

    def update_family_member(self, member, earning_status: bool = True, earnings: float = 0.0):
        # accept member instance or id
        member_id = getattr(member, "id", None) or member
        if member_id is None:
            # try lookup by name
            if hasattr(member, "name"):
                candidates = [m for m in self.members if m.name == member.name]
                if candidates:
                    member_id = candidates[0].id
        if member_id is None:
            return False
        ok = self._backend.update_family_member(member_id, earning_status, earnings)
        self.refresh()
        return ok

    def calculate_total_earnings(self) -> float:
        return self._backend.calculate_total_earnings()

    # -------- Expenses / Log API (map to backend) --------
    def add_expense(self, value, category, description, date_obj_or_str, frequency="One-time", paid_by="Unknown"):
        # maintain the same validation semantics
        if value == 0:
            raise ValueError("Value cannot be zero")
        if not str(category).strip():
            raise ValueError("Please choose a category")
        txn_id = self._backend.add_expense(value, category, description, date_obj_or_str, frequency, paid_by)
        self.refresh()
        return txn_id

    def merge_similar_category(self, value, category, description, date_obj_or_str, frequency="One-time", paid_by="Unknown"):
        """
        Kept for API parity with previous code. Backed by add_expense + aggregated view.
        """
        return self.add_expense(value, category, description, date_obj_or_str, frequency, paid_by)

    def delete_expense(self, expense):
        """
        In original code delete_expense removed aggregated item; replicate by deleting all transactions
        for that category (same semantic as the backend.delete_expense).
        """
        category = getattr(expense, "category", None)
        if not category:
            return 0
        deleted_count = self._backend.delete_expense(category)
        self.refresh()
        return deleted_count

    def delete_log_entry(self, log_entry):
        """
        log_entry should be an Expense with an id (coming from DB). Delete that DB row.
        """
        txn_id = getattr(log_entry, "id", None)
        if txn_id is None:
            # cannot delete log entry without id
            raise ValueError("Log entry doesn't have an id. Cannot delete.")
        ok = self._backend.delete_log_entry(txn_id)
        self.refresh()
        return ok

    def calculate_total_expenditure(self) -> float:
        return self._backend.calculate_total_expenditure()

    # ---- Utilities ----
    def export_csv_bytes(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> bytes:
        """Return CSV bytes from backend export_csv (useful for streamlit download)."""
        return self._backend.export_csv(start_date=start_date, end_date=end_date)

    def close(self):
        """Closes backend resources if needed."""
        try:
            self._backend.close()
        except Exception:
            pass


# For quick testing when running main.py directly
if __name__ == "__main__":
    fet = FamilyExpenseTracker(auto_seed=True)
    print("Members:", [m.name for m in fet.members])
    print("Aggregated:", [(e.category, e.value) for e in fet.expense_list])
    print("Log count:", len(fet.expense_log))
