import streamlit as st
from main import FamilyExpenseTracker
import matplotlib.pyplot as plt
from streamlit_option_menu import option_menu
from pathlib import Path
import datetime
import pandas as pd
import io

# Streamlit configuration
st.set_page_config(page_title="Family Expense Tracker", page_icon="💰", layout="wide")
# st.title("")

# Path Settings
current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
css_file = current_dir / "styles" / "main.css"

with open(css_file) as f:
    st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

# Create a session state object
session_state = st.session_state

# Check if the 'expense_tracker' object exists in the session state
if "expense_tracker" not in session_state:
    session_state.expense_tracker = FamilyExpenseTracker()

# Center-align the heading using HTML
st.markdown(
    '<h1 style="text-align: center;">Family Expense Tracker</h1>',
    unsafe_allow_html=True,
)

# Navigation Menu
selected = option_menu(
    menu_title=None,
    options=["Data Entry", "Data Overview", "Data Visualization"],
    icons=[
        "pencil-fill",
        "clipboard2-data",
        "bar-chart-fill",
    ],
    orientation="horizontal",
)

# Access the 'expense_tracker' object from session state
expense_tracker = session_state.expense_tracker

if selected == "Data Entry":
    st.header("Add Family Member")
    with st.expander("Add Family Member"):
        member_name = st.text_input("Name").title()
        earning_status = st.checkbox("Earning Status")
        if earning_status:
            earnings = st.number_input("Earnings", value=1, min_value=1)
        else:
            earnings = 0

        if st.button("Add Member"):
            try:
                member = [
                    member
                    for member in expense_tracker.members
                    if member.name == member_name
                ]
                if not member:
                    expense_tracker.add_family_member(
                        member_name, earning_status, earnings
                    )
                    st.success("Member added successfully!")
                else:
                    expense_tracker.update_family_member(
                        member[0], earning_status, earnings
                    )
                    st.success("Member updated successfully!")
            except ValueError as e:
                st.error(str(e))

    # Sidebar for adding expenses
    st.header("Add Expenses")
    with st.expander("Add Expenses"):
        # --- CHANGE: Check for members first ---
        if not expense_tracker.members:
            st.warning("Please add at least one family member above before adding expenses.")
        else:
            # --- CHANGE: Select who is paying ---
            member_names = [m.name for m in expense_tracker.members]
            paid_by = st.selectbox("Paid By", member_names)

            expense_category = st.selectbox(
                "Category",
                (
                    "Housing",
                    "Food",
                    "Transportation",
                    "Entertainment",
                    "Child-Related",
                    "Medical",
                    "Investment",
                    "Miscellaneous",
                ),
            )
            expense_description = st.text_input("Description (optional)").title()
            expense_value = st.number_input("Value", min_value=0)
            expense_date = st.date_input("Date", value=datetime.date.today())

            expense_frequency = st.selectbox(
                "Payment frequency",
                ("One-time", "Monthly", "Quarterly", "Yearly"),
                index=None,
                placeholder="Select frequency...",
            )

            if st.button("Add Expense"):
                if not expense_frequency:
                     st.error("Please select a payment frequency")
                else:
                    try:
                        # --- CHANGE: Pass 'paid_by' to the function ---
                        expense_tracker.merge_similar_category(
                            expense_value,
                            expense_category,
                            expense_description,
                            expense_date,
                            expense_frequency,
                            paid_by, 
                        )
                        st.success("Expense added successfully!")
                    except ValueError as e:
                        st.error(str(e))

elif selected == "Data Overview":
    # Display family members
    if not expense_tracker.members:
        st.info(
            "Start by adding family members to track your expenses together! Currently, no members have been added."
        )
    else:
        st.header("Family Members")
        
        # --- FIX: ALIGNMENT FOR FAMILY MEMBERS ---
        # Giving 'Action' more space (last column)
        col_ratios_members = [1.5, 1.5, 1, 2] 
        
        (
            name_column,
            earning_status_column,
            earnings_column,
            family_delete_column,
        ) = st.columns(col_ratios_members)
        
        name_column.write("**Name**")
        earning_status_column.write("**Earning status**")
        earnings_column.write("**Earnings**")
        family_delete_column.write("**Action**")

        for member in expense_tracker.members:
            cols = st.columns(col_ratios_members) # Use same ratio loop
            cols[0].write(member.name)
            cols[1].write("Earning" if member.earning_status else "Not Earning")
            cols[2].write(member.earnings)

            if cols[3].button(f"Delete member: {member.name}"):
                expense_tracker.delete_family_member(member)
                st.rerun()

        # Display aggregated expenses (by category)
        st.header("Expenses (Aggregated by Category)")
        if not expense_tracker.expense_list:
            st.info("Currently, no expenses have been added.")
        else:
            col_ratios = [1, 2, 3, 1.5, 1.5, 1]
            
            (
                value_column,
                category_column,
                description_column,
                date_column,
                frequency_column,
                expense_delete_column,
            ) = st.columns(col_ratios)
            
            value_column.write("**Value**")
            category_column.write("**Category**")
            description_column.write("**Description**")
            date_column.write("**Date**")
            frequency_column.write("**Frequency**")
            expense_delete_column.write("**Delete**")

            for idx, expense in enumerate(expense_tracker.expense_list):
                cols = st.columns(col_ratios) 
                cols[0].write(expense.value)
                cols[1].write(expense.category)
                cols[2].write(expense.description)
                cols[3].write(expense.date)
                cols[4].write(getattr(expense, "frequency", "One-time"))

                if cols[5].button(f"Delete agg {idx}"):
                    expense_tracker.delete_expense(expense)
                    st.rerun()

        # Totals
        total_earnings = expense_tracker.calculate_total_earnings()
        total_expenditure = expense_tracker.calculate_total_expenditure()
        remaining_balance = total_earnings - total_expenditure
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Earnings", f"{total_earnings}")
        col2.metric("Total Expenditure", f"{total_expenditure}")
        col3.metric("Remaining Balance", f"{remaining_balance}")

        # --- CHANGE: LOG INSIDE EXPANDER + 'PAID BY' COLUMN ---
        st.header("Payment Log")
        with st.expander("View Detailed Payment History"):
            if not expense_tracker.expense_log:
                st.info("No payments recorded yet.")
            else:
                df = pd.DataFrame(
                    [
                        {
                            "Date": e.date,
                            "Paid By": getattr(e, "paid_by", "Unknown"), # Added
                            "Category": e.category,
                            "Description": e.description,
                            "Value": e.value,
                            "Frequency": e.frequency,
                        }
                        for e in expense_tracker.expense_log
                    ]
                )

                st.dataframe(df)

                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue().encode("utf-8")

                st.download_button(
                    label="Download log (CSV)",
                    data=csv_data,
                    file_name=f"expense_log_{datetime.date.today().isoformat()}.csv",
                    mime="text/csv",
                )

                st.write("Delete specific log entries:")
                # Updated columns to include 'Paid By'
                for idx, log_entry in enumerate(list(expense_tracker.expense_log)):
                    cols = st.columns([2, 2, 2, 1, 1, 1])
                    cols[0].write(log_entry.date)
                    cols[1].write(getattr(log_entry, "paid_by", "Unknown"))
                    cols[2].write(log_entry.category)
                    cols[3].write(log_entry.value)
                    cols[4].write(log_entry.frequency)
                    if cols[5].button(f"Delete log {idx}"):
                        expense_tracker.delete_log_entry(log_entry)
                        st.success("Log entry deleted.")
                        st.rerun()

elif selected == "Data Visualization":
    expense_data = [
        (expense.category, expense.value) for expense in expense_tracker.expense_list
    ]
    if expense_data:
        expenses = [data[0] for data in expense_data]
        values = [data[1] for data in expense_data]
        total = sum(values)
        if total <= 0:
            st.info("No expense values to visualize.")
        else:
            percentages = [(value / total) * 100 for value in values]
            fig, ax = plt.subplots(figsize=(3, 3), dpi=300)
            ax.pie(
                percentages,
                labels=expenses,
                autopct="%1.1f%%",
                startangle=140,
                textprops={"fontsize": 6, "color": "white"},
            )
            ax.set_title("Expense Distribution", fontsize=12, color="white")
            fig.patch.set_facecolor("none")
            st.pyplot(fig)
    else:
        st.info(
            "Start by adding family members to track your expenses together!"
        )
