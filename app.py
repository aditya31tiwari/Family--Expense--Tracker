import streamlit as st
from main import FamilyExpenseTracker
import matplotlib.pyplot as plt
from streamlit_option_menu import option_menu
from pathlib import Path
import datetime
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go

# Streamlit configuration
st.set_page_config(
    page_title="Family Expense Tracker", 
    page_icon="💰", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better responsiveness and styling
st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 1rem;
    }
    
    /* Title styling */
    .main-title {
        text-align: center;
        color: #1f77b4;
        font-size: clamp(1.5rem, 4vw, 3rem);
        font-weight: 700;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Card styling */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.2);
    }
    
    .metric-value {
        font-size: clamp(1.5rem, 3vw, 2.5rem);
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: clamp(0.9rem, 2vw, 1.1rem);
        opacity: 0.9;
    }
    
    /* Section headers */
    .section-header {
        color: #2c3e50;
        font-size: clamp(1.2rem, 2.5vw, 1.8rem);
        font-weight: 600;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #3498db;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* DataFrame styling */
    .dataframe {
        font-size: clamp(0.8rem, 1.5vw, 1rem);
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 10px;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .main {
            padding: 0.5rem;
        }
        
        .metric-card {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .section-header {
            margin: 1.5rem 0 0.8rem 0;
        }
    }
    
    /* Tablet responsiveness */
    @media (min-width: 769px) and (max-width: 1024px) {
        .main {
            padding: 1.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if "expense_tracker" not in st.session_state:
    st.session_state.expense_tracker = FamilyExpenseTracker()

# Title
st.markdown('<h1 class="main-title"> Family Expense Tracker</h1>', unsafe_allow_html=True)

# Navigation Menu with responsive styling
selected = option_menu(
    menu_title=None,
    options=["Data Entry", "Overview", "Analytics"],
    icons=["pencil-fill", "clipboard2-data", "bar-chart-fill"],
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#f8f9fa"},
        "icon": {"color": "#3498db", "font-size": "clamp(16px, 2vw, 20px)"},
        "nav-link": {
            "font-size": "clamp(14px, 1.8vw, 18px)",
            "text-align": "center",
            "margin": "0px",
            "padding": "0.8rem 1rem",
            "--hover-color": "#e8f4f8",
        },
        "nav-link-selected": {"background-color": "#3498db"},
    },
)

# Access the expense_tracker from session state
expense_tracker = st.session_state.expense_tracker

# ==================== DATA ENTRY ====================
if selected == "Data Entry":
    # Responsive layout: stacks on mobile, side-by-side on desktop
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown('<div class="section-header">👥 Add Family Member</div>', unsafe_allow_html=True)
        with st.expander("➕ Add or Update Member", expanded=True):
            member_name = st.text_input("👤 Name", key="member_name", placeholder="Enter name...").strip().title()
            earning_status = st.checkbox("💼 Is Earning?", key="earning_status")
            
            if earning_status:
                earnings = st.number_input(
                    "💵 Monthly Earnings (₹)", 
                    value=0, 
                    min_value=0, 
                    step=1000,
                    key="earnings",
                    help="Enter monthly income"
                )
            else:
                earnings = 0

            if st.button("✅ Add/Update Member", type="primary", use_container_width=True):
                if not member_name:
                    st.error("❌ Please enter a name")
                else:
                    try:
                        existing_member = expense_tracker.get_member_by_name(member_name)
                        
                        if existing_member:
                            expense_tracker.update_family_member(
                                existing_member, earning_status, earnings
                            )
                            st.success(f"✅ Member '{member_name}' updated!")
                        else:
                            expense_tracker.add_family_member(
                                member_name, earning_status, earnings
                            )
                            st.success(f"✅ Member '{member_name}' added!")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"❌ {str(e)}")

    with col2:
        st.markdown('<div class="section-header">💸 Add Expenses</div>', unsafe_allow_html=True)
        with st.expander("➕ Add New Expense", expanded=True):
            if not expense_tracker.members:
                st.warning("⚠ Please add at least one family member first.")
            else:
                member_names = [m.name for m in expense_tracker.members]
                paid_by = st.selectbox("👤 Paid By", member_names, key="paid_by")

                expense_category = st.selectbox(
                    "📁 Category",
                    [
                        "🏠 Housing",
                        "🍔 Food",
                        "🚗 Transportation",
                        "🎬 Entertainment",
                        "👶 Child-Related",
                        "🏥 Medical",
                        "📈 Investment",
                        "⚡ Utilities",
                        "📚 Education",
                        "🔧 Miscellaneous",
                    ],
                    key="category"
                )
                
                # Clean category (remove emoji)
                clean_category = expense_category.split(" ", 1)[1] if " " in expense_category else expense_category
                
                expense_description = st.text_input(
                    "📝 Description (optional)", 
                    key="description",
                    placeholder="Add details..."
                ).strip().title()
                
                col_a, col_b = st.columns(2)
                with col_a:
                    expense_value = st.number_input(
                        "💰 Amount (₹)", 
                        min_value=0.0, 
                        step=100.0,
                        key="value"
                    )
                
                with col_b:
                    expense_date = st.date_input(
                        "📅 Date", 
                        value=datetime.date.today(), 
                        format="DD/MM/YYYY",
                        key="date"
                    )

                expense_frequency = st.selectbox(
                    "🔄 Payment Frequency",
                    ["One-time", "Monthly", "Quarterly", "Yearly"],
                    key="frequency"
                )

                if st.button("✅ Add Expense", type="primary", use_container_width=True):
                    if expense_value <= 0:
                        st.error("❌ Amount must be greater than zero")
                    else:
                        try:
                            expense_tracker.merge_similar_category(
                                expense_value,
                                clean_category,
                                expense_description,
                                expense_date,
                                expense_frequency,
                                paid_by,
                            )
                            st.success(f"✅ Expense of ₹{expense_value:,.0f} added!")
                            st.rerun()
                        except ValueError as e:
                            st.error(f"❌ {str(e)}")

# ==================== DATA OVERVIEW ====================
elif selected == "Overview":
    if not expense_tracker.members:
        st.info(
            "👋 Welcome! Start by adding family members in the 'Data Entry' tab."
        )
    else:
        # Summary Cards - Responsive Grid
        stats = expense_tracker.get_summary_stats()
        
        # Create responsive columns
        cols = st.columns([1, 1, 1, 1])
        
        metrics_data = [
            ("👥", "Members", stats['total_members'], "#667eea"),
            ("💰", "Earnings", f"₹{stats['total_earnings']:,.0f}", "#2ecc71"),
            ("💸", "Expenses", f"₹{stats['total_expenses']:,.0f}", "#e74c3c"),
            ("💵", "Balance", f"₹{stats['balance']:,.0f}", "#3498db" if stats['balance'] >= 0 else "#e74c3c")
        ]
        
        for col, (icon, label, value, color) in zip(cols, metrics_data):
            with col:
                st.markdown(f"""
                <div class="metric-card" style="background: linear-gradient(135deg, {color} 0%, {color}dd 100%);">
                    <div style="font-size: 2rem;">{icon}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Family Members Section
        st.markdown('<div class="section-header">👥 Family Members</div>', unsafe_allow_html=True)
        
        if expense_tracker.members:
            # Responsive table
            members_data = []
            for member in expense_tracker.members:
                members_data.append({
                    "👤 Name": member.name,
                    "💼 Status": "✅ Earning" if member.earning_status else "❌ Not Earning",
                    "💰 Earnings": f"₹{member.earnings:,.0f}",
                    "💸 Contributed": f"₹{expense_tracker.calculate_member_contribution(member.name):,.0f}"
                })
            
            df_members = pd.DataFrame(members_data)
            st.dataframe(df_members, use_container_width=True, hide_index=True)
            
            # Delete member section
            with st.expander("🗑 Delete Member"):
                col_del1, col_del2 = st.columns([3, 1])
                with col_del1:
                    member_to_delete = st.selectbox(
                        "Select member",
                        [m.name for m in expense_tracker.members],
                        key="delete_member_select",
                        label_visibility="collapsed"
                    )
                with col_del2:
                    if st.button("Delete", type="secondary", use_container_width=True):
                        member = expense_tracker.get_member_by_name(member_to_delete)
                        if member:
                            expense_tracker.delete_family_member(member)
                            st.success(f"✅ Deleted!")
                            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Aggregated Expenses
        st.markdown('<div class="section-header">📊 Expenses by Category</div>', unsafe_allow_html=True)
        
        if not expense_tracker.expense_list:
            st.info("📝 No expenses yet. Add some in the 'Data Entry' tab.")
        else:
            expenses_data = []
            for idx, expense in enumerate(expense_tracker.expense_list):
                date_display = expense.date.strftime("%d-%m-%Y") if isinstance(expense.date, datetime.date) else expense.date
                expenses_data.append({
                    "📁 Category": expense.category,
                    "📝 Description": expense.description,
                    "💰 Amount": f"₹{expense.value:,.0f}",
                    "📅 Date": date_display,
                    "🔄 Frequency": expense.frequency,
                })
            
            df_expenses = pd.DataFrame(expenses_data)
            st.dataframe(df_expenses, use_container_width=True, hide_index=True)
            
            # Delete expense section
            with st.expander("🗑 Delete Category Expense"):
                col_del1, col_del2 = st.columns([3, 1])
                with col_del1:
                    expense_to_delete = st.selectbox(
                        "Select category",
                        [f"{e.category} (₹{e.value:,.0f})" for e in expense_tracker.expense_list],
                        key="delete_expense_select",
                        label_visibility="collapsed"
                    )
                with col_del2:
                    if st.button("Delete", type="secondary", use_container_width=True, key="del_exp"):
                        category = expense_to_delete.split(" (")[0]
                        for expense in expense_tracker.expense_list:
                            if expense.category == category:
                                expense_tracker.delete_expense(expense)
                                st.success(f"✅ Deleted!")
                                st.rerun()
                                break
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Payment Log
        st.markdown('<div class="section-header">📜 Payment History</div>', unsafe_allow_html=True)
        with st.expander("View Complete Log", expanded=False):
            if not expense_tracker.expense_log:
                st.info("📝 No payment records yet.")
            else:
                log_data = []
                for log_entry in expense_tracker.expense_log:
                    date_display = log_entry.date.strftime("%d-%m-%Y") if isinstance(log_entry.date, datetime.date) else log_entry.date
                    log_data.append({
                        "📅 Date": date_display,
                        "👤 Paid By": log_entry.paid_by,
                        "📁 Category": log_entry.category,
                        "📝 Description": log_entry.description,
                        "💰 Amount": f"₹{log_entry.value:,.0f}",
                        "🔄 Frequency": log_entry.frequency
                    })
                
                df_log = pd.DataFrame(log_data)
                st.dataframe(df_log, use_container_width=True, hide_index=True)
                
                # Prepare CSV
                csv_buffer = io.StringIO()
                df_log.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue().encode("utf-8")
                
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"expense_log_{datetime.date.today().strftime('%d-%m-%Y')}.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )

# ==================== DATA VISUALIZATION ====================
elif selected == "Analytics":
    st.markdown('<div class="section-header">📊 Expense Analytics</div>', unsafe_allow_html=True)
    
    if not expense_tracker.expense_list:
        st.info("📝 No data to visualize. Add expenses to see analytics.")
    else:
        # Tab-based visualization for better mobile experience
        tab1, tab3 = st.tabs(["📊 Distribution", "👥 Contributions"])
        
        with tab1:
            # Responsive columns
            col1, col2 = st.columns([1, 1], gap="large")
            
            with col1:
                st.subheader("Expense by Category")
                expenses = [exp.category for exp in expense_tracker.expense_list]
                values = [exp.value for exp in expense_tracker.expense_list]
                
                # Using Plotly for interactive charts
                fig = px.pie(
                    values=values,
                    names=expenses,
                    title="",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    showlegend=True,
                    height=400,
                    margin=dict(t=0, b=0, l=0, r=0)
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Amount by Category")
                
                # Bar chart
                fig = px.bar(
                    x=values,
                    y=expenses,
                    orientation='h',
                    title="",
                    labels={'x': 'Amount (₹)', 'y': 'Category'},
                    color=values,
                    color_continuous_scale='Blues'
                )
                fig.update_layout(
                    showlegend=False,
                    height=400,
                    margin=dict(t=0, b=0, l=0, r=0)
                )
                st.plotly_chart(fig, use_container_width=True)
        
        
        with tab3:
            st.subheader("Member Contributions")
            
            if expense_tracker.members:
                member_contributions = {}
                for member in expense_tracker.members:
                    contribution = expense_tracker.calculate_member_contribution(member.name)
                    member_contributions[member.name] = contribution
                
                if any(member_contributions.values()):
                    members = list(member_contributions.keys())
                    contributions = list(member_contributions.values())
                    
                    # Contribution bar chart
                    fig = px.bar(
                        x=members,
                        y=contributions,
                        title="",
                        labels={'x': 'Member', 'y': 'Total Contribution (₹)'},
                        color=contributions,
                        color_continuous_scale='Greens'
                    )
                    fig.update_layout(
                        height=400,
                        showlegend=False,
                        margin=dict(t=0, b=0, l=0, r=0)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Contribution percentage
                    total_contributions = sum(contributions)
                    if total_contributions > 0:
                        st.subheader("Contribution Share")
                        
                        fig = go.Figure(data=[go.Pie(
                            labels=members,
                            values=contributions,
                            hole=.3,
                            marker_colors=px.colors.sequential.Greens
                        )])
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        fig.update_layout(
                            height=400,
                            margin=dict(t=0, b=0, l=0, r=0),
                            showlegend=True
                        )
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No contributions recorded yet.")
