import pandas as pd
import plotly.express as px
import joblib
from prophet import Prophet
import plotly.graph_objects as go
import plotly.figure_factory as ff
import numpy as np
import calendar
import datetime
import json
import sys
import os
import threading
import time
from functools import lru_cache

# Import functions from utils instead of sum.py
from utils import categorize, normalize_transaction, clean_text, EXCLUDE_CATEGORIES, load_data, CONFIG

# Load model and vectorizer for backward compatibility
model = joblib.load("category_classifier_model.pkl")
vectorizer = joblib.load("tfidf_vectorizer.pkl")

# Cache for Prophet models
forecast_cache = {}
forecast_lock = threading.Lock()
FORECAST_EXPIRY = 3600  # Cache forecasts for 1 hour

# Function to get or create a cached forecast
def get_cached_forecast(cache_key, data_func, *args, **kwargs):
    global forecast_cache
    current_time = time.time()
    
    with forecast_lock:
        # Remove expired forecasts
        expired_keys = [k for k, v in forecast_cache.items() if current_time - v.get('timestamp', 0) > FORECAST_EXPIRY]
        for k in expired_keys:
            del forecast_cache[k]
        
        # Check if forecast exists in cache
        if cache_key in forecast_cache:
            return forecast_cache[cache_key]['forecast']
    
    # Create new forecast if not in cache
    forecast_data = data_func(*args, **kwargs)
    
    with forecast_lock:
        forecast_cache[cache_key] = {
            'forecast': forecast_data,
            'timestamp': current_time
        }
    
    return forecast_data


def forecast_spending(df, months_ahead=3):
    """Forecast overall spending with caching support"""
    # Create a cache key based on the dataframe hash and months ahead
    cache_key = f"overall_forecast_{hash(str(df.shape))}_{months_ahead}"
    
    # Define the actual forecast function
    def _create_forecast():
        df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
        
        # Use the constant from utils
        expense_df = df[~df["Category"].isin(EXCLUDE_CATEGORIES)]
        
        # Use Normalized_Amount and take absolute value for forecast
        monthly_df = expense_df.groupby("Month")["Normalized_Amount"].sum().abs().reset_index()
        monthly_df.columns = ["ds", "y"]
        
        model = Prophet()
        model.fit(monthly_df)
        
        future = model.make_future_dataframe(periods=months_ahead, freq="MS")
        forecast = model.predict(future)
        
        # Plotly interactive forecast chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=monthly_df["ds"],
            y=monthly_df["y"],
            mode="lines+markers",
            name="Actual",
            line=dict(color="blue"),
            hovertemplate="Date: %{x}<br>Actual: %{y:.2f}<extra></extra>"
        ))
        
        fig.add_trace(go.Scatter(
            x=forecast["ds"],
            y=forecast["yhat"],
            mode="lines",
            name="Forecast",
            line=dict(color="green", dash="dash"),
            hovertemplate="Date: %{x}<br>Forecast: %{y:.2f}<extra></extra>"
        ))
        
        fig.add_trace(go.Scatter(
            x=forecast["ds"],
            y=forecast["yhat_upper"],
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=forecast["ds"],
            y=forecast["yhat_lower"],
            fill='tonexty',
            fillcolor='rgba(0, 255, 0, 0.1)',
            line=dict(width=0),
            name='Uncertainty',
            hoverinfo='skip'
        ))
        
        fig.update_layout(
            title="🔮 Forecast of Future Spending (Excludes Income & Papa Transfer)",
            xaxis_title="Date",
            yaxis_title="Amount ($)",
            hovermode="x unified"
        )
        
        return fig.to_html(full_html=False)
    
    # Get or create the forecast using our caching system
    return get_cached_forecast(cache_key, _create_forecast)


def income_vs_expenses(df):
    """Compare income and expenses over time"""
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    
    # Group by month and category type
    income_df = df[df["Predicted Category"].isin(["Income", "Papa Transfer"])]
    expense_df = df[~df["Predicted Category"].isin(["Income", "Papa Transfer"])]
    
    income_monthly = income_df.groupby("Month")["Amount"].sum().reset_index()
    income_monthly["Type"] = "Income"
    
    expense_monthly = expense_df.groupby("Month")["Amount"].sum().reset_index()
    expense_monthly["Type"] = "Expenses"
    
    combined = pd.concat([income_monthly, expense_monthly])
    
    # Calculate savings
    pivoted = combined.pivot(index="Month", columns="Type", values="Amount").reset_index()
    pivoted["Savings"] = pivoted["Income"] - pivoted["Expenses"]
    pivoted["Savings Rate"] = (pivoted["Income"] - pivoted["Expenses"]) / pivoted["Income"] * 100
    
    # Create figure
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=pivoted["Month"],
        y=pivoted["Income"],
        name="Income",
        marker_color="green"
    ))
    
    fig.add_trace(go.Bar(
        x=pivoted["Month"],
        y=pivoted["Expenses"],
        name="Expenses",
        marker_color="red"
    ))
    
    fig.add_trace(go.Scatter(
        x=pivoted["Month"],
        y=pivoted["Savings"],
        mode="lines+markers",
        name="Savings",
        marker_color="blue",
        yaxis="y2"
    ))
    
    fig.update_layout(
        title="Income vs. Expenses Over Time",
        xaxis_title="Month",
        yaxis_title="Amount ($)",
        yaxis2=dict(
            title="Savings ($)",
            overlaying="y",
            side="right"
        ),
        barmode="group",
        hovermode="x unified"
    )
    
    return fig.to_html(full_html=False)


def essential_vs_discretionary(df):
    """Create a gauge showing the ratio of essential vs discretionary spending"""
    # Define essential and discretionary categories
    essential = ["Groceries", "Rent", "Utilities", "Transport", "Tuition", "Pharmacy"]
    
    # Filter and calculate
    expense_df = df[~df["Predicted Category"].isin(["Income", "Papa Transfer"])]
    essential_spending = expense_df[expense_df["Predicted Category"].isin(essential)]["Amount"].sum()
    total_spending = expense_df["Amount"].sum()
    essential_ratio = essential_spending / total_spending * 100
    
    # Create gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=essential_ratio,
        title={"text": "Essential Spending Ratio"},
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [0, 50], "color": "lightgreen"},
                {"range": [50, 75], "color": "yellow"},
                {"range": [75, 100], "color": "orange"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 80
            }
        }
    ))
    
    fig.update_layout(
        title="Essential vs. Discretionary Spending",
        height=300
    )
    
    return fig.to_html(full_html=False)


def dining_vs_groceries(df):
    """Compare spending on groceries vs dining out"""
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    
    # Filter for relevant categories
    food_df = df[df["Predicted Category"].isin(["Groceries", "Food & Dining"])]
    
    # Group by month and category
    monthly_food = food_df.groupby(["Month", "Predicted Category"])["Amount"].sum().reset_index()
    
    # Create figure
    fig = px.line(
        monthly_food, 
        x="Month", 
        y="Amount", 
        color="Predicted Category",
        title="Groceries vs. Dining Out",
        markers=True
    )
    
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Amount ($)",
        hovermode="x unified"
    )
    
    return fig.to_html(full_html=False)


def spending_calendar(df):
    """Create a calendar heatmap of daily spending"""
    # Create a copy of data with just the date and amount
    current_year = datetime.datetime.now().year
    calendar_df = df[~df["Predicted Category"].isin(["Income", "Papa Transfer"])].copy()
    calendar_df = calendar_df[calendar_df["Date"].dt.year == current_year]
    
    # Group by date
    daily_spend = calendar_df.groupby(calendar_df["Date"].dt.date)["Amount"].sum().reset_index()
    daily_spend.columns = ["Date", "Amount"]
    
    # Create the necessary format for the calendar heatmap
    daily_spend["Month"] = pd.to_datetime(daily_spend["Date"]).dt.month
    daily_spend["Weekday"] = pd.to_datetime(daily_spend["Date"]).dt.dayofweek
    daily_spend["WeekdayName"] = pd.to_datetime(daily_spend["Date"]).dt.day_name()
    daily_spend["MonthName"] = pd.to_datetime(daily_spend["Date"]).dt.month_name()
    daily_spend["Day"] = pd.to_datetime(daily_spend["Date"]).dt.day
    
    # Prepare the heatmap
    z_data = []
    month_names = []
    
    for month in range(1, 13):
        month_data = daily_spend[daily_spend["Month"] == month]
        if not month_data.empty:
            month_names.append(calendar.month_name[month])
            month_array = np.zeros(7)
            for _, row in month_data.iterrows():
                month_array[row["Weekday"]] += row["Amount"]
            z_data.append(month_array)
    
    if not z_data:  # Handle case with no data
        return "<p>No data available for calendar view this year.</p>"
    
    fig = ff.create_annotated_heatmap(
        z=z_data,
        x=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        y=month_names,
        colorscale="Blues",
        annotation_text=None,
        showscale=True
    )
    
    fig.update_layout(
        title="Spending Heatmap by Day of Week",
        height=500
    )
    
    return fig.to_html(full_html=False)


def top_spending_categories(df):
    """Show the top 3 spending categories with details"""
    expense_df = df[~df["Predicted Category"].isin(["Income", "Papa Transfer"])]
    category_totals = expense_df.groupby("Predicted Category")["Amount"].sum().reset_index()
    category_totals = category_totals.sort_values("Amount", ascending=False).head(3)
    
    fig = px.bar(
        category_totals,
        x="Predicted Category",
        y="Amount",
        color="Predicted Category",
        text="Amount",
        title="Top 3 Spending Categories"
    )
    
    fig.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
    
    fig.update_layout(
        xaxis_title="Category",
        yaxis_title="Total Amount ($)",
        showlegend=False,
        height=400
    )
    
    return fig.to_html(full_html=False)


def category_growth(df):
    """Show month-over-month growth for each category"""
    # Prepare data
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    expense_df = df[~df["Predicted Category"].isin(["Income", "Papa Transfer"])]
    
    # Group by month and category
    monthly_cat = expense_df.groupby(["Month", "Predicted Category"])["Amount"].sum().reset_index()
    
    # Calculate growth rates
    growth_data = []
    
    for category in monthly_cat["Predicted Category"].unique():
        cat_data = monthly_cat[monthly_cat["Predicted Category"] == category].sort_values("Month")
        
        if len(cat_data) > 1:
            cat_data["Growth"] = cat_data["Amount"].pct_change() * 100
            last_growth = cat_data["Growth"].iloc[-1]
            last_amount = cat_data["Amount"].iloc[-1]
            
            growth_data.append({
                "Category": category,
                "Growth": last_growth,
                "Amount": last_amount
            })
    
    growth_df = pd.DataFrame(growth_data)
    
    if growth_df.empty:
        return "<p>Insufficient data for growth calculations.</p>"
    
    # Create chart
    fig = go.Figure()
    
    for _, row in growth_df.iterrows():
        color = "green" if row["Growth"] < 0 else "red"
        fig.add_trace(go.Indicator(
            mode="delta",
            value=row["Growth"],
            delta={"reference": 0, "position": "top"},
            title={
                "text": f"<b>{row['Category']}</b><br><span style='font-size:0.8em'>${row['Amount']:.2f}</span>"
            },
            domain={"row": 0, "column": _}
        ))
    
    fig.update_layout(
        grid={"rows": 1, "columns": len(growth_df)},
        title="Category MoM Growth",
        height=250
    )
    
    return fig.to_html(full_html=False)


def sankey_income_allocation(df):
    """Create a Sankey diagram showing flow from income to spending categories"""
    # Filter data
    income_categories = ["Income", "Papa Transfer"]
    expense_categories = [cat for cat in df["Predicted Category"].unique() if cat not in income_categories]
    
    # Calculate total income and expenses by category
    income_total = df[df["Predicted Category"].isin(income_categories)]["Amount"].sum()
    expenses_by_cat = df[df["Predicted Category"].isin(expense_categories)].groupby("Predicted Category")["Amount"].sum().reset_index()
    
    # Create Sankey data
    labels = income_categories + expense_categories
    
    # Source nodes (income categories)
    source = []
    for _ in range(len(expense_categories)):
        source.append(0)  # All expenses come from "Income" (node 0)
    
    # Target nodes (expense categories)
    target = []
    for i in range(len(expense_categories)):
        target.append(i + len(income_categories))
    
    # Values (amounts)
    value = expenses_by_cat["Amount"].tolist()
    
    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=labels
        ),
        link=dict(
            source=source,
            target=target,
            value=value
        )
    )])
    
    fig.update_layout(
        title="Income Allocation Flow",
        font_size=10,
        height=500
    )
    
    return fig.to_html(full_html=False)


def category_forecast(df, category, months_ahead=3):
    """Forecast spending for a specific category with caching"""
    # Create a cache key based on category, dataframe shape and months ahead
    cache_key = f"{category}_forecast_{hash(str(df.shape))}_{months_ahead}"
    
    # Define the actual forecast function
    def _create_forecast():
        df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
        cat_df = df[df["Predicted Category"] == category]
        
        if len(cat_df) < 3:  # Need minimum data for forecasting
            return f"<p>Insufficient data for {category} forecast.</p>"
        
        monthly_df = cat_df.groupby("Month")["Amount"].sum().reset_index()
        monthly_df.columns = ["ds", "y"]
        
        model = Prophet()
        model.fit(monthly_df)
        
        future = model.make_future_dataframe(periods=months_ahead, freq="MS")
        forecast = model.predict(future)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=monthly_df["ds"],
            y=monthly_df["y"],
            mode="lines+markers",
            name="Actual",
            line=dict(color="blue"),
            hovertemplate="Date: %{x}<br>Actual: %{y:.2f}<extra></extra>"
        ))
        
        fig.add_trace(go.Scatter(
            x=forecast["ds"],
            y=forecast["yhat"],
            mode="lines",
            name="Forecast",
            line=dict(color="green", dash="dash"),
            hovertemplate="Date: %{x}<br>Forecast: %{y:.2f}<extra></extra>"
        ))
        
        fig.add_trace(go.Scatter(
            x=forecast["ds"],
            y=forecast["yhat_upper"],
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=forecast["ds"],
            y=forecast["yhat_lower"],
            fill='tonexty',
            fillcolor='rgba(0, 255, 0, 0.1)',
            line=dict(width=0),
            name='Uncertainty',
            hoverinfo='skip'
        ))
        
        fig.update_layout(
            title=f"🔮 {category} Spending Forecast",
            xaxis_title="Date",
            yaxis_title="Amount ($)",
            hovermode="x unified"
        )
        
        return fig.to_html(full_html=False)
    
    # Get or create the forecast using our caching system
    return get_cached_forecast(cache_key, _create_forecast)

def transaction_table(df):
    """
    Create an interactive table view of transactions with filtering capabilities.
    
    Args:
        df: Dataframe containing transaction data with Standardized_Amount
    
    Returns:
        HTML string containing the interactive table
    """
    import plotly.graph_objects as go
    import pandas as pd
    
    # Create a copy of the dataframe with relevant columns
    table_df = df[["Date", "Amount", "Type", "Description", "Bank", "Predicted Category", "Standardized_Amount"]].copy()
    
    # Format the date column
    table_df["Date"] = pd.to_datetime(table_df["Date"]).dt.strftime('%Y-%m-%d')
    
    # Format the amount columns to show currency
    table_df["Amount"] = table_df["Amount"].apply(lambda x: f"${x:.2f}")
    table_df["Standardized_Amount"] = table_df["Standardized_Amount"].apply(lambda x: f"${x:.2f}")
    
    # Create the table figure
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=list(table_df.columns),
            fill_color='#444444',
            font=dict(color='white', size=14),
            align=['left', 'right', 'left', 'left', 'left', 'left', 'right']
        ),
        cells=dict(
            values=[table_df[col] for col in table_df.columns],
            fill_color=[['#f9f9f9', '#ffffff']*len(table_df)],
            font=dict(color='#444444', size=12),
            align=['left', 'right', 'left', 'left', 'left', 'left', 'right'],
            height=30
        )
    )])
    
    # Update the layout
    fig.update_layout(
        title="Transaction Details",
        margin=dict(l=10, r=10, t=40, b=10),
        height=600
    )
    
    # Create dropdown filters for specific columns
    category_options = sorted(df["Predicted Category"].unique())
    bank_options = sorted(df["Bank"].unique())
    type_options = sorted(df["Type"].unique())
    
    # Generate a unique ID for this table instance
    import uuid
    table_id = f"transaction-table-{uuid.uuid4().hex[:8]}"
    
    filter_html = f"""
    <div style="display: flex; justify-content: space-between; margin-bottom: 15px; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 200px; margin-right: 10px;">
            <label for="category-filter-{table_id}">Category:</label>
            <select id="category-filter-{table_id}" class="filter-{table_id}" style="width: 100%; padding: 5px;">
                <option value="">All Categories</option>
                {"".join([f'<option value="{cat}">{cat}</option>' for cat in category_options])}
            </select>
        </div>
        <div style="flex: 1; min-width: 200px; margin-right: 10px;">
            <label for="bank-filter-{table_id}">Bank:</label>
            <select id="bank-filter-{table_id}" class="filter-{table_id}" style="width: 100%; padding: 5px;">
                <option value="">All Banks</option>
                {"".join([f'<option value="{bank}">{bank}</option>' for bank in bank_options])}
            </select>
        </div>
        <div style="flex: 1; min-width: 200px; margin-right: 10px;">
            <label for="type-filter-{table_id}">Transaction Type:</label>
            <select id="type-filter-{table_id}" class="filter-{table_id}" style="width: 100%; padding: 5px;">
                <option value="">All Types</option>
                {"".join([f'<option value="{t}">{t}</option>' for t in type_options])}
            </select>
        </div>
    </div>
    <div style="margin-bottom: 15px;">
        <button id="reset-filters-{table_id}" style="padding: 5px 15px;">Reset Filters</button>
    </div>
    """
    
    # Create JavaScript for filtering
    js_code = f"""
    <script>
        // Wait for the document to be fully loaded
        document.addEventListener('DOMContentLoaded', function() {{
            // Setup the filtering functionality once the page is interactive
            setTimeout(function() {{
                setupTableFilters("{table_id}");
            }}, 1000);
        }});
        
        // Function to set up table filters
        function setupTableFilters(tableId) {{
            const tableContainer = document.getElementById(tableId);
            if (!tableContainer) return;
            
            // Store original table HTML for reset function
            const originalTable = tableContainer.innerHTML;
            
            function filterTable() {{
                const categoryFilter = document.getElementById('category-filter-' + tableId).value;
                const bankFilter = document.getElementById('bank-filter-' + tableId).value;
                const typeFilter = document.getElementById('type-filter-' + tableId).value;
                
                // Get all rows from the table
                const table = tableContainer.querySelector('table');
                if (!table) return;
                
                const tbody = table.querySelector('tbody');
                if (!tbody) return;
                
                const rows = tbody.querySelectorAll('tr');
                if (!rows || rows.length === 0) return;
                
                // Filter each row
                rows.forEach(row => {{
                    let cells = row.querySelectorAll('td');
                    if (cells.length === 0) return; // Skip header rows
                    
                    // Get cell values - adjust indices if table structure changes
                    const date = cells[0].textContent.trim();
                    const amount = cells[1].textContent.trim();
                    const type = cells[2].textContent.trim();
                    const description = cells[3].textContent.trim();
                    const bank = cells[4].textContent.trim();
                    const category = cells[5].textContent.trim();
                    
                    // Apply filters
                    let visible = true;
                    
                    if (categoryFilter && category !== categoryFilter) visible = false;
                    if (bankFilter && bank !== bankFilter) visible = false;
                    if (typeFilter && type !== typeFilter) visible = false;
                    
                    // Show or hide the row
                    row.style.display = visible ? '' : 'none';
                }});
            }}
            
            // Add event listeners to all filters
            const filters = document.querySelectorAll('.filter-' + tableId);
            filters.forEach(filter => {{
                filter.addEventListener('change', filterTable);
            }});
            
            // Reset filters button
            const resetButton = document.getElementById('reset-filters-' + tableId);
            if (resetButton) {{
                resetButton.addEventListener('click', function() {{
                    // Reset dropdown selections
                    filters.forEach(filter => {{
                        filter.selectedIndex = 0;
                    }});
                    
                    // Show all rows
                    const table = tableContainer.querySelector('table');
                    if (table) {{
                        const rows = table.querySelectorAll('tbody tr');
                        rows.forEach(row => {{
                            row.style.display = '';
                        }});
                    }}
                }});
            }}
            
            console.log('Table filters initialized for ' + tableId);
        }}
    </script>
    """
    
    # Combine filter HTML, table, and JavaScript
    complete_html = f"""
    <div class="card mb-4">
        <div class="card-body">
            <h3 class="card-title">Transaction Explorer</h3>
            {filter_html}
            <div id="{table_id}">
                {fig.to_html(full_html=False)}
            </div>
            {js_code}
        </div>
    </div>
    """
    
    return complete_html

def generate_dashboard(csv_path):
    # Try to load config like in sum.py
    try:
        with open("creds.json") as creds:
            config = json.load(creds)
    except:
        config = {}  # Empty config if file not found
    
    # Load data
    df = pd.read_csv(csv_path, encoding="ISO-8859-1")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df.dropna(subset=["Date", "Description", "Amount"], inplace=True)

    # Ensure all amounts are positive initially (just like in sum.py)
    df["Amount"] = df["Amount"].abs()

    # Use the categorization and normalization from sum.py
    result = df.apply(normalize_transaction, axis=1)
    df["Category"] = result["Category"]
    df["Normalized_Amount"] = result["Normalized_Amount"]
    
    # For backward compatibility, set Predicted Category to be the same as Category
    df["Predicted Category"] = df["Category"]
    df["Standardized_Amount"] = df["Normalized_Amount"]  # For backward compatibility
    
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    # Calculate income and expenses using normalized amounts
    income_df = df[df["Category"] == "Income"]
    papa_transfer_df = df[df["Category"] == "Papa Transfer"] if "Papa Transfer" in df["Category"].unique() else pd.DataFrame()
    internal_transfer_df = df[df["Category"] == "Internal Transfer"]
    
    # For income, we use the positive normalized amounts
    total_income = income_df["Normalized_Amount"].sum()
    total_papa = papa_transfer_df["Normalized_Amount"].sum() if not papa_transfer_df.empty else 0
    
    # For expenses, we use the negative normalized amounts (they're already negative)
    expense_df = df[~df["Category"].isin(["Income", "Papa Transfer", "Internal Transfer"])]
    total_expenses = expense_df["Normalized_Amount"].sum()
    
    # Calculate savings and savings rate 
    savings = total_income + total_papa + total_expenses  # Expenses are already negative
    savings_rate = (savings / (total_income + total_papa)) * 100 if (total_income + total_papa) > 0 else 0

    # Create a copy of df for visualizations
    df_viz = df.copy()
    
    # Create expense_df_viz with absolute values for visualization
    expense_df_viz = expense_df.copy()
    expense_df_viz["Amount"] = expense_df_viz["Normalized_Amount"].abs()

    # Enhanced visualizations - update to use Category instead of Predicted Category
    pie_html = px.pie(expense_df_viz, names="Category", values="Amount", 
                      title="Spend by Category", hole=0.4).to_html(full_html=False)
    
    bar_data = expense_df_viz.groupby(["Month", "Category"])["Amount"].sum().reset_index()
    bar_html = px.bar(bar_data, x="Month", y="Amount", color="Category", 
                      barmode="stack", title="Monthly Expense Trends").to_html(full_html=False)
    
    # Generate other visualizations with normalized amounts
    forecast_html = forecast_spending(df_viz)
    income_vs_expenses_html = income_vs_expenses(df_viz)
    essential_vs_disc_html = essential_vs_discretionary(df_viz)
    dining_vs_groceries_html = dining_vs_groceries(df_viz)
    calendar_html = spending_calendar(df_viz)
    top_categories_html = top_spending_categories(df_viz)
    growth_html = category_growth(df_viz)
    sankey_html = sankey_income_allocation(df_viz)
    
    # Generate transaction table with filtering capabilities
    transaction_table_html = transaction_table(df_viz)
    
    # Category-specific forecasts
    rent_forecast_html = category_forecast(df_viz, "Rent")
    food_forecast_html = category_forecast(df_viz, "Food & Dining")
    
    return {
        "pie_chart": pie_html,
        "bar_chart": bar_html,
        "forecast": forecast_html,
        "income_vs_expenses": income_vs_expenses_html,
        "essential_ratio": essential_vs_disc_html,
        "dining_vs_groceries": dining_vs_groceries_html,
        "calendar": calendar_html,
        "top_categories": top_categories_html,
        "category_growth": growth_html,
        "income_flow": sankey_html,
        "rent_forecast": rent_forecast_html,
        "food_forecast": food_forecast_html,
        "transaction_table": transaction_table_html,
        "summary_stats": {
            "total_income": round(total_income, 2),
            "total_papa_transfer": round(total_papa, 2),
            "total_expenses": round(abs(total_expenses), 2),  # Make positive for display
            "savings": round(savings, 2),
            "savings_rate": round(savings_rate, 2)
        }
    }
