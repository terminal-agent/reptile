import plotly.graph_objects as go

from .token_budget import TokenBudgetManager


class BudgetProgressChart:
  """
  A class to visualize budget progress chart (Frontend).
  Focuses purely on chart rendering and UI updates.
  """

  def __init__(
    self,
    budget_manager: TokenBudgetManager,
    chart_size: int = 150,
  ):
    """
    Initialize the Budget Progress Chart.
    Args:
        budget_manager: Backend token budget manager
        chart_size: Size of the chart (height and width)
    """
    self.budget_manager = budget_manager
    self.chart_size = chart_size

  def get_budget_chart(self):
    """Returns only the chart figure."""
    return self.create_chart()

  def create_chart(self) -> go.Figure:
    """
    Creates a circular budget progress chart using budget manager's data.
    Returns:
        A Plotly Figure object representing the circular progress bar.
    """
    stats = self.budget_manager.get_budget_stats()
    return self.update_chart(
      budget_spent=stats["budget_spent"], total_budget=stats["total_budget"]
    )

  def update_chart(self, budget_spent: int, total_budget: int = 0) -> go.Figure:
    """
    Creates a circular budget progress chart using a Plotly pie chart.
    Args:
        budget_spent: The amount of money spent.
        total_budget: The total budget amount. If 0, uses budget manager's max limit.
    Returns:
        A Plotly Figure object representing the circular progress bar.
    """
    if total_budget == 0:
      total_budget = self.budget_manager.max_token_limit
    remaining_budget = max(0, total_budget - budget_spent)
    percentage_spent = (
      (budget_spent / total_budget) * 100 if total_budget > 0 else 0
    )

    # Ensure the percentage does not exceed 100%
    if percentage_spent > 100:
      percentage_spent = 100

    # Create the pie chart for the progress bar
    fig = go.Figure(
      go.Pie(
        values=[budget_spent, remaining_budget],
        labels=["Spent", "Remaining"],
        hole=0.8,  # This creates the circular bar effect
        marker={
          "colors": ["#3498db", "#ecf0f1"]
        },  # Set colors for spent and remaining
        hoverinfo="label+percent",
        textinfo="none",  # Don't show text inside the chart slices
      )
    )

    # Display the percentage and budget amount in the center of the chart
    if total_budget == 0:
      annotation_text = "Waiting for start..."
    else:
      annotation_text = f"{budget_spent}<br>/<br>{total_budget}"

    fig.add_annotation(
      text=annotation_text,
      x=0.5,
      y=0.55,
      font_size=12,
      showarrow=False,
    )

    # Customize the layout and hide the modebar
    fig.update_layout(
      title={"text": "Token Used", "x": 0.5, "xanchor": "center"},
      showlegend=False,
      margin=dict(t=30, b=10, l=0, r=0),
      height=self.chart_size,
      width=self.chart_size,
      modebar={
        "remove": [
          "zoom",
          "pan",
          "select",
          "lasso2d",
          "zoomIn",
          "zoomOut",
          "autoScale",
          "resetScale",
        ]
      },
      xaxis={"visible": False},
      yaxis={"visible": False},
    )

    # Completely disable modebar
    fig.layout.updatemenus = []

    return fig
