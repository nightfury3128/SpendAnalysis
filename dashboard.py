import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import logging

logger = logging.getLogger(__name__)

def generate_dashboard(csv_file="account.csv"):
    try:
        df = pd.read_csv(csv_file)

        # Clean and prepare data
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        df.dropna(subset=["Date", "Amount"], inplace=True)
        df["Month"] = df["Date"].dt.to_period("M")

        # Group by Month and Type
        summary = df.groupby(["Month", "Type"])["Amount"].sum().unstack(fill_value=0)

        # Plot
        fig, ax = plt.subplots(figsize=(10, 5))
        summary.plot(kind="bar", stacked=True, ax=ax)
        ax.set_title("Monthly Income vs Expenses")
        ax.set_ylabel("Amount ($)")
        plt.xticks(rotation=45)

        # Save plot to base64
        img = BytesIO()
        plt.tight_layout()
        plt.savefig(img, format="png")
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()

        html = f"""
        <h2>📊 Income vs Expenses</h2>
        <img src='data:image/png;base64,{plot_url}'/>
        """

        return html
    except Exception as e:
        logger.exception("Failed to generate dashboard.")
        return f"<h3>Error generating dashboard: {e}</h3>"
