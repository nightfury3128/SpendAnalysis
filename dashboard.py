import pandas as pd
import plotly.express as px
import joblib
from prophet import Prophet
import plotly.graph_objects as go


# Load model and vectorizer
model = joblib.load("category_classifier_model.pkl")
vectorizer = joblib.load("tfidf_vectorizer.pkl")


def clean_text(text):
    return text.lower()


def forecast_spending(df, months_ahead=3):
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()

    # ✅ Exclude both 'Income' and 'Papa Transfer'
    exclude_categories = ["Income", "Papa Transfer"]
    expense_df = df[~df["Predicted Category"].isin(exclude_categories)]

    monthly_df = expense_df.groupby("Month")["Amount"].sum().reset_index()
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


def generate_dashboard(csv_path):
    # Load data
    df = pd.read_csv(csv_path, encoding="ISO-8859-1")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df.dropna(subset=["Date", "Description", "Amount"], inplace=True)

    # Predict category
    df["Cleaned_Description"] = df["Description"].apply(clean_text)
    df["Predicted Category"] = model.predict(vectorizer.transform(df["Cleaned_Description"]))
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    # Separate income and expenses
    expense_df = df[df["Predicted Category"] != "Income"]
    income_df = df[df["Predicted Category"] == "Income"]
    total_income = income_df["Amount"].sum()

    # Pie chart
    pie_fig = px.pie(expense_df, names="Predicted Category", values="Amount", title="Spend by Category", hole=0.4)
    pie_html = pie_fig.to_html(full_html=False)

    # Monthly stacked bar
    monthly_grouped = expense_df.groupby(["Month", "Predicted Category"])["Amount"].sum().reset_index()
    bar_fig = px.bar(monthly_grouped, x="Month", y="Amount", color="Predicted Category",
                     barmode="stack", title="Monthly Expense Trends")
    bar_html = bar_fig.to_html(full_html=False)

    # Forecast
    forecast_html = forecast_spending(df)

    return pie_html, bar_html, forecast_html, df, round(total_income, 2)
