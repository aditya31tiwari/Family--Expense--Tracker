# main.py
from datetime import datetime, date
from typing import Optional, List, Dict
from backend import Backend  # must be your existing backend.py

# ---- Domain classes (compatible with her app.py) ----
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

    def __eq__(self, other):
        if isinstance(other, FamilyMember):
            return self.name.lower() == other.name.lower()
        return False

    def __hash__(self):
        return hash(self.name.lower())


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
        if value is None:
            raise ValueError("Value cannot be None")
        self.id = id
        self.value = float(value)
        self.category = category
        self.description = description if description else "No description"

        # Normalize date to datetime.date where possible
        if isinstance(date_obj_or_str, date):
            self.date = date_obj_or_str
        else:
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

    def __eq__(self, other):
        if isinstance(other, Expense):
            return (
                self.value == other.value
                and self.category == other.category
                and str(self.date) == str(other.date)
                and self.paid_by == other.paid_by
            )
        return False


# ---- Wrapper using Backend (keeps API expected by the app) ----
class FamilyExpenseTracker:
    def __init__(self, auto_seed: bool = False):
        self._backend = Backend(auto_init=True, auto_seed=auto_seed)
        self.members: List[FamilyMember] = []
        self.expense_list: List[Expense] = []
        self.expense_log: List[Expense] = []
        self.refresh()

    def refresh(self):
        # reload members
        self.members = []
        for m in self._backend.get_members():
            fm = FamilyMember(name=m["name"], earning_status=m["earning_status"], earnings=m["earnings"], id=m["id"])
            self.members.append(fm)

        # aggregated (category sums)
        self.expense_list = []
        for a in self._backend.get_aggregated_expenses():
            e = Expense(value=a["value"], category=a["category"], description=a.get("description", ""), date_obj_or_str=date.today(), frequency="One-time", paid_by="Unknown")
            self.expense_list.append(e)

        # raw chronological log
        self.expense_log = []
        for r in self._backend.get_expense_log():
            dt = r["date"]
            d_obj = None
            try:
                d_obj = datetime.fromisoformat(dt).date()
            except Exception:
                try:
                    d_obj = datetime.strptime(dt, "%d-%m-%Y").date()
                except Exception:
                    d_obj = dt
            exp = Expense(value=r["value"], category=r["category"], description=r["description"], date_obj_or_str=d_obj, frequency=r.get("frequency", "One-time"), paid_by=r.get("paid_by", "Unknown"), id=r["id"])
            self.expense_log.append(exp)

    # --- Members ---
    def add_family_member(self, name: str, earning_status: bool = True, earnings: float = 0.0):
        if not str(name).strip():
            raise ValueError("Name field cannot be empty")
        _id = self._backend.add_family_member(name.strip(), earning_status, earnings)
        self.refresh()
        return _id

    def get_member_by_name(self, name: str) -> Optional[FamilyMember]:
        for m in self.members:
            if m.name.lower() == name.lower():
                return m
        return None

    def delete_family_member(self, member):
        member_id = getattr(member, "id", None) or (member.name if hasattr(member, "name") else member)
        if isinstance(member_id, str):
            m = self.get_member_by_name(member_id)
            member_id = getattr(m, "id", None) if m else None
        ok = False
        if member_id is not None:
            ok = self._backend.delete_family_member(member_id)
        self.refresh()
        return ok

    def update_family_member(self, member, earning_status: bool = True, earnings: float = 0.0):
        member_id = getattr(member, "id", None) or (member.name if hasattr(member, "name") else member)
        if isinstance(member_id, str):
            m = self.get_member_by_name(member_id)
            member_id = getattr(m, "id", None) if m else None
        if member_id is None:
            return False
        ok = self._backend.update_family_member(member_id, earning_status, earnings)
        self.refresh()
        return ok

    def calculate_total_earnings(self) -> float:
        return self._backend.calculate_total_earnings()

    # --- Expenses / Log ---
    def add_expense(self, value, category, description, date_obj_or_str, frequency="One-time", paid_by="Unknown"):
        if value == 0 or value is None:
            raise ValueError("Value cannot be zero")
        if not str(category).strip():
            raise ValueError("Please choose a category")
        txn_id = self._backend.add_expense(value, category, description, date_obj_or_str, frequency, paid_by)
        self.refresh()
        return txn_id

    def merge_similar_category(self, value, category, description, date_obj_or_str, frequency="One-time", paid_by="Unknown"):
        # same semantics: add a transaction and aggregated view will reflect it
        return self.add_expense(value, category, description, date_obj_or_str, frequency, paid_by)

    def delete_expense(self, expense):
        # remove all transactions for a category (same semantic as earlier aggregated delete)
        category = getattr(expense, "category", None)
        if not category:
            return 0
        deleted = self._backend.delete_expense(category)
        self.refresh()
        return deleted

    def delete_log_entry(self, log_entry):
        txn_id = getattr(log_entry, "id", None)
        if txn_id is None:
            raise ValueError("Log entry doesn't have an id. Cannot delete.")
        ok = self._backend.delete_log_entry(txn_id)
        self.refresh()
        return ok

    def calculate_total_expenditure(self) -> float:
        return self._backend.calculate_total_expenditure()

    # helpers expected by her UI
    def get_expenses_by_category(self, category: str):
        return [exp for exp in self.expense_list if exp.category == category]

    def get_expenses_by_member(self, member_name: str):
        return [exp for exp in self.expense_log if exp.paid_by == member_name]

    def calculate_member_contribution(self, member_name: str) -> float:
        return sum(exp.value for exp in self.expense_log if exp.paid_by == member_name)

    def get_summary_stats(self) -> Dict:
        total_members = len(self.members)
        earning_members = sum(1 for m in self.members if m.earning_status)
        total_earnings = self.calculate_total_earnings()
        total_expenses = self.calculate_total_expenditure()
        balance = total_earnings - total_expenses
        return {
            "total_members": total_members,
            "earning_members": earning_members,
            "total_earnings": total_earnings,
            "total_expenses": total_expenses,
            "balance": balance,
            "total_transactions": len(self.expense_log),
            "categories_used": len(set(e.category for e in self.expense_list)),
        }

    # export utility for Streamlit download buttons
    def export_csv_bytes(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> bytes:
        return self._backend.export_csv(start_date=start_date, end_date=end_date)

    def close(self):
        try:
            self._backend.close()
        except Exception:
            pass


# quick local test
if __name__ == "__main__":
    fet = FamilyExpenseTracker(auto_seed=True)
    print("Members:", [m.name for m in fet.members])
    print("Aggregated:", [(e.category, e.value) for e in fet.expense_list])
    print("Log count:", len(fet.expense_log))
