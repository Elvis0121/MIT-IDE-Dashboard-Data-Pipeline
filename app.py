import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp

# Load pre-processed data
def load_data():
    # Publications and Citations Data
    rgl_publications = pd.DataFrame({
        'Year': [2020, 2021, 2022, 2023, 2024, 2025],
        'Value': [110, 117, 74, 106, 115, 30]
    })
    or_publications = pd.DataFrame({
        'Year': [2020, 2021, 2022, 2023, 2024, 2025],
        'Value': [247, 209, 209, 220, 206, 81]
    })
    combined_publications = pd.DataFrame({
        'Year': [2020, 2021, 2022, 2023, 2024, 2025],
        'Value': [357, 326, 283, 326, 321, 111]
    })
    rgl_citations = pd.DataFrame({
        'Year': [2020, 2021, 2022, 2023, 2024, 2025],
        'Value': [22786, 9619, 2329, 3529, 2057, 31]
    })
    or_citations = pd.DataFrame({
        'Year': [2020, 2021, 2022, 2023, 2024, 2025],
        'Value': [28216, 8280, 10621, 3953, 4368, 827]
    })
    combined_citations = pd.DataFrame({
        'Year': [2020, 2021, 2022, 2023, 2024, 2025],
        'Value': [51002, 17899, 12950, 7482, 6425, 858]
    })

    # YouTube Data
    youtube_data = pd.DataFrame({
        'Years': ['2020', '2021', '2022', '2023', '2024', '2025'],
        'Videos': [19, 7, 51, 37, 27, 0],
        'Views': [5270, 1397, 11674, 16927, 5580, 0]
    })

    # Medium Data
    medium_data = pd.DataFrame({
        'Years': ['2019', '2020', '2021', '2022', '2023'], 
        'Articles': [1, 5, 5, 6, 3], 
        'Claps': [3, 36, 13, 130, 5]
    })

    # Eventbrite Data
    eventbrite_data = pd.DataFrame({
        'Year': [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        'Total Attendees': [150, 200, 250, 300, 400, 350, 500, 450, 300, 400, 380]
    })

    # Budget Data
    budget_data = pd.DataFrame({
        'Year': ['2020', '2021', '2022', '2023', '2024', '2025'],
        'Budget (Millions)': [2.59, 2.44, 3.95, 3.85, 3.53, 4.63]
    })

    return (combined_publications, combined_citations,
            youtube_data, medium_data, eventbrite_data,
            budget_data)

# Load data
(combined_publications, combined_citations,
 youtube_data, medium_data, eventbrite_data,
 budget_data) = load_data()

# Set page config
st.set_page_config(layout="wide")

# Custom CSS to control the width of the main content
st.markdown("""
    <style>
        .main .block-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("MIT IDE Growth Metrics Dashboard")

# Function to create cumulative line chart
def create_cumulative_chart(df, x_col, y_col, title, color=None, y_label=None):
    # Calculate cumulative sum
    df_cum = df.copy()
    df_cum['Cumulative'] = df_cum[y_col].cumsum()
    
    # Convert x values to integers if they're years
    if x_col in ['Year', 'Years']:
        df_cum[x_col] = df_cum[x_col].astype(int)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_cum[x_col],
        y=df_cum['Cumulative'],
        mode='lines+markers',
        name=title,
        line=dict(width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font=dict(size=20)
        ),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="center",
            x=0.5,
            orientation="h",
            font=dict(size=12)
        ),
        height=450,
        margin=dict(l=50, r=50, t=80, b=50),
        xaxis=dict(
            showgrid=True, 
            gridwidth=1, 
            gridcolor='rgba(128, 128, 128, 0.2)',
            title="Year",
            tickmode='linear',
            tick0=df_cum[x_col].min(),
            dtick=1,
            title_font=dict(size=14),
            tickfont=dict(size=12)
        ),
        yaxis=dict(
            showgrid=True, 
            gridwidth=1, 
            gridcolor='rgba(128, 128, 128, 0.2)',
            title=y_label or "Count",
            title_font=dict(size=14),
            tickfont=dict(size=12)
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    if color:
        fig.update_traces(line_color=color)
    
    return fig

# Create and display charts in a single column layout with centered content
for header, chart_args in [
    ("Publications Growth", (combined_publications, 'Year', 'Value', 'Total Publications', '#1f77b4', "Publications")),
    ("Citations Growth", (combined_citations, 'Year', 'Value', 'Total Citations', '#2ca02c', "Citations")),
    ("Content Engagement Growth", (youtube_data, 'Years', 'Views', 'YouTube Views', '#d62728', "Views")),
    ("Medium Engagement Growth", (medium_data, 'Years', 'Claps', 'Medium Claps', '#ff7f0e', "Claps")),
    ("Community Growth", (eventbrite_data, 'Year', 'Total Attendees', 'Event Attendees', '#9467bd', "Attendees")),
    ("Resource Growth", (budget_data, 'Year', 'Budget (Millions)', 'Budget', '#e377c2', "Budget (Millions)"))
]:
    st.header(header)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.plotly_chart(create_cumulative_chart(*chart_args), use_container_width=True)
    st.markdown("---")  # Add a separator between charts
