import streamlit as st
import requests, json
import pandas as pd
import datetime as dt
from src.general_functions import get_general_layout
import plotly.express as px
import plotly.graph_objs as go
import plotly
from streamlit_extras.chart_container import chart_container

st.set_page_config(
    page_title="Nordic Flow-based Web app",
    page_icon="https://i.imgur.com/Kd4P3y2.png",
    layout='wide',
    initial_sidebar_state='expanded'
)

start_date, end_date = get_general_layout()

st.markdown(f"This tool visualizes Nordic Flow-based data that has been part of the market coupling process.")





@st.cache_data(show_spinner=False, max_entries=100)
def get_puto_data(start, end):
    start_str = start.strftime("%Y-%m-%dT") + "00:00:00"
    end_str = end.strftime("%Y-%m-%dT") + "23:59:00"
    url = (f"https://publicationtool.jao.eu/nordic/api/data/fbDomainShadowPrice?Filter=%7B%22NonRedundant%22%3Atrue%7D&"
           f"Skip=0&Take=10000&FromUtc={start_str}.000Z&ToUtc={end_str}.000Z")
    res = requests.api.get(url)
    res_decoded = res.content.decode('utf-8')

    response = json.loads(res_decoded)
    print(response.keys())
    df = pd.DataFrame(response['data'])
    # if 'totalRowsWithFilter' is more than 10000, get the rest of the data until all rows are fetched
    if response['totalRowsWithFilter'] > 10000:
        skip = 10000
        while skip < response['totalRowsWithFilter']:
            url = (f"https://publicationtool.jao.eu/nordic/api/data/fbDomainShadowPrice?Filter=%7B%22NonRedundant%22%3Atrue%7D&"
                   f"Skip={skip}&Take=10000&FromUtc={start_str}.000Z&ToUtc={end_str}.000Z")
            res = requests.api.get(url)
            res_decoded = res.content.decode('utf-8')
            response = json.loads(res_decoded)
            df = pd.concat([df, pd.DataFrame(response['data'])])
            skip += 10000
    return df

data = get_puto_data(start_date, end_date)
data['dateTimeUtc'] = pd.to_datetime(data['dateTimeUtc'])
data.set_index('dateTimeUtc', inplace=True)
# Add multi-select filter for 'tso'
tso_filter = st.sidebar.multiselect('Select TSO(s)', data['tso'].unique())
# Filter data based on selected 'tso'
if len(tso_filter) > 0:
    data = data[data['tso'].isin(tso_filter)]
#st.dataframe(data)
tab1, tab2 = st.tabs(['Shadow price', 'Data for selected CNECs'],)
with tab1:
    shadow_prices = data.groupby(["dateTimeUtc", "cnecName"])["shadowPrice"].sum().reset_index()

    shadow_prices.set_index('dateTimeUtc', inplace=True)
    #filt
    shadow_prices = shadow_prices[shadow_prices['shadowPrice']>0.01]

    with chart_container(data, ["Chart 📈", "Data 📄", "Download 📁"], ["CSV"]):
        shadow_prices = shadow_prices.sort_values('shadowPrice', ascending=True)
        fig = px.bar(shadow_prices, y='cnecName', x='shadowPrice', orientation='h', hover_data=[shadow_prices.index],
                    title="Cumulative shadow prices for each CNE", height=1000)

        st.plotly_chart(fig, use_container_width=True)
        #plot each cnec shadow price
        cnecs = shadow_prices['cnecName'].unique()
        fig2 = go.Figure()
        for cnec in cnecs:
            temp_data = shadow_prices[shadow_prices['cnecName'] == cnec]
            temp_data = temp_data.resample('H').mean(numeric_only=True)
            
            fig2.add_trace(go.Scatter(x=temp_data.index, y=temp_data['shadowPrice'], mode='markers+lines', name=cnec,
                                    connectgaps=False))

        fig2.update_layout(dict(yaxis_title='Shadow Price €/MW', xaxis_title='Time', legend_title="CNEC name"
                                ,hovermode="x unified"))
        st.plotly_chart(fig2, use_container_width=True)

with tab2:
    # Create filter for 'cnecName'
    cnec_filter = st.multiselect('Select CNEC(s)', data['cnecName'].unique())

    # Create multiselect for other columns except 'cnecName'
    cols = data.columns.tolist()
    cols.remove('cnecName')

    col_filter = st.multiselect('Select columns to graph', cols)
    # Create line plot using selected filters using plotly
    if len(cnec_filter) > 0 and len(col_filter) > 0:
        filtered_data = data[data['cnecName'].isin(cnec_filter)]
        fig3 = go.Figure()
        for cnec in cnec_filter:
            temp_data = filtered_data[filtered_data['cnecName'] == cnec]
            # resample data to hourly
            temp_data = temp_data.resample('H').mean(numeric_only=True)
            # filter date range
            temp_data = temp_data[start_date:end_date]
            for col in col_filter:
                fig3.add_trace(go.Scatter(x=temp_data.index, y=temp_data[col], mode='markers+lines', name=f"{cnec} {col}",
                                        connectgaps=False))
        fig3.update_layout(dict(yaxis_title='Value', xaxis_title='Time', legend_title="CNEC name and column",
                                hovermode="x unified"))
        st.plotly_chart(fig3, use_container_width=True)
