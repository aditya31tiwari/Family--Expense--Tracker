# main.py

class FamilyMember:
    def __init__(self, name, earning_status=True, earnings=0):
        self.name = name
        self.earning_status = earning_status
        self.earnings = earnings

    def __str__(self):
        return (
            f"Name: {self.name}, Earning Status: {'Earning' if self.earning_status else 'Not Earning'}, "
            f"Earnings: {self.earnings}"
        )


class Expense:
    def __init__(self, value, category, description, date, frequency="One-time"):
        """
        frequency: "One-time", "Quarterly", or "Yearly"
        """
        self.value = value
        self.category = category
        self.description = description
        self.date = date
        self.frequency = frequency

    def __str__(self):
        return (
            f"Value: {self.value}, Category: {self.category}, Description: {self.description}, "
            f"Date: {self.date}, Frequency: {self.frequency}"
        )


class FamilyExpenseTracker:
    def __init__(self):
        # Aggregated display list (current UI uses this)
        self.members = []
        self.expense_list = []
        # Raw chronological log of every payment (for download / exact history)
        self.expense_log = []

    # --- Members ---
    def add_family_member(self, name, earning_status=True, earnings=0):
        if not name.strip():
            raise ValueError("Name field cannot be empty")

        member = FamilyMember(name, earning_status, earnings)
        self.members.append(member)

    def delete_family_member(self, member):
        self.members.remove(member)

    def update_family_member(self, member, earning_status=True, earnings=0):
        if member:
            member.earning_status = earning_status
            member.earnings = earnings

    def calculate_total_earnings(self):
        total_earnings = sum(
            member.earnings for member in self.members if member.earning_status
        )
        return total_earnings

    # --- Expenses / Log ---
    def add_expense(self, value, category, description, date, frequency="One-time"):
        if value == 0:
            raise ValueError("Value cannot be zero")
        if not category.strip():
            raise ValueError("Please choose a category")

        expense = Expense(value, category, description, date, frequency)
        self.expense_list.append(expense)
        # Always append to the raw log as well
        self.expense_log.append(Expense(value, category, description, date, frequency))

    def delete_expense(self, expense):
        """Delete from aggregated expense_list (used by aggregated table delete)."""
        if expense in self.expense_list:
            self.expense_list.remove(expense)

    def delete_log_entry(self, log_entry):
        """
        Delete a single raw log entry and propagate the change to the aggregated list:
        - Remove the log entry
        - Subtract its value from the aggregated expense for that category
        - If aggregated value becomes <= 0, remove that aggregated entry
        """
        if log_entry in self.expense_log:
            # Remove from raw log
            self.expense_log.remove(log_entry)

            # Find aggregated entry with same category
            agg = None
            for e in self.expense_list:
                if e.category == log_entry.category:
                    agg = e
                    break

            if agg:
                agg.value -= log_entry.value
                # If aggregated goes to zero or negative, remove it
                if agg.value <= 0:
                    try:
                        self.expense_list.remove(agg)
                    except ValueError:
                        pass

    def merge_similar_category(self, value, category, description, date, frequency="One-time"):
        """
        Keep merge-by-category for the aggregated view, but append a raw log entry only once.
        If category already exists -> update aggregator and append a raw log entry.
        If category is new -> call add_expense(...) which already adds both aggregator and raw log.
        """
        if value == 0:
            raise ValueError("Value cannot be zero")
        if not category.strip():
            raise ValueError("Please choose a category")

        existing_expense = None
        for expense in self.expense_list:
            if expense.category == category:
                existing_expense = expense
                break

        if existing_expense:
            existing_expense.value += value
            if description:
                existing_expense.description = description
            # Append single raw log entry for this submission
            self.expense_log.append(Expense(value, category, description, date, frequency))
        else:
            # Create aggregated entry and raw log via add_expense (add_expense already appends to expense_log)
            self.add_expense(value, category, description, date, frequency)

    def calculate_total_expenditure(self):
        total_expenditure = sum(expense.value for expense in self.expense_list)
        return total_expenditure


if __name__ == "__main__":
    expense_tracker = FamilyExpenseTracker()
