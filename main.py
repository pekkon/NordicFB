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


import os

@st.cache_data(show_spinner=False, max_entries=100)
def get_puto_data(start, end):
    csv_filename = "puto_data.csv"
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    start_str = start_ts.strftime("%Y-%m-%dT") + "00:00:00"
    end_str = end_ts.strftime("%Y-%m-%dT") + "23:59:00"
    mybar = st.progress(0, text="Loading data...")

    # If file exists, check date coverage
    if os.path.exists(csv_filename):
        mybar.progress(0.1, text="Reading cached CSV...")
        df = pd.read_csv(csv_filename, parse_dates=['dateTimeUtc'])
        df['dateTimeUtc'] = pd.to_datetime(df['dateTimeUtc'])
        df['dateTimeUtc'] = df['dateTimeUtc'].dt.tz_localize(None)
        df = df.sort_values('dateTimeUtc')
        file_start = df['dateTimeUtc'].min()
        file_end = df['dateTimeUtc'].max()

        # If file covers requested range, return only relevant data
        if file_start <= start_ts and file_end >= end_ts:
            mybar.progress(1.0, text="Loaded cached data from CSV.")
            st.info(f"Loaded cached data from {csv_filename}")
            mask = (df['dateTimeUtc'] >= start_ts) & (df['dateTimeUtc'] <= end_ts)
            return df.loc[mask].reset_index(drop=True)

        # Otherwise, download missing data
        missing_ranges = []
        if start_ts < file_start:
            missing_ranges.append((start_ts, file_start - pd.Timedelta(seconds=1)))
        if end_ts > file_end:
            missing_ranges.append((file_end + pd.Timedelta(seconds=1), end_ts))

        new_data = []
        for idx, (rng_start, rng_end) in enumerate(missing_ranges):
            rng_start_str = rng_start.strftime("%Y-%m-%dT") + "00:00:00"
            rng_end_str = rng_end.strftime("%Y-%m-%dT") + "23:59:00"
            url = (f"https://publicationtool.jao.eu/nordic/api/data/fbDomainShadowPrice?Filter=%7B%22NonRedundant%22%3Atrue%7D&"
                   f"Skip=0&Take=10000&FromUtc={rng_start_str}.000Z&ToUtc={rng_end_str}.000Z")
            mybar.progress(0.2 + idx*0.2, text=f"Downloading missing data from {rng_start_str} to {rng_end_str}...")
            res = requests.api.get(url)
            res_decoded = res.content.decode('utf-8')
            response = json.loads(res_decoded)
            temp_df = pd.DataFrame(response['data'])
            total_len = response['totalRowsWithFilter']
            skip = 10000
            while total_len > skip:
                mybar.progress(min(0.8, 0.2 + idx*0.2 + skip/total_len*0.2), text=f"Downloading data from {rng_start_str} to {rng_end_str}... ({skip}/{total_len})")
                url = (f"https://publicationtool.jao.eu/nordic/api/data/fbDomainShadowPrice?Filter=%7B%22NonRedundant%22%3Atrue%7D&"
                       f"Skip={skip}&Take=10000&FromUtc={rng_start_str}.000Z&ToUtc={rng_end_str}.000Z")
                res = requests.api.get(url)
                res_decoded = res.content.decode('utf-8')
                response = json.loads(res_decoded)
                temp_df = pd.concat([temp_df, pd.DataFrame(response['data'])])
                skip += 10000
            new_data.append(temp_df)

        if new_data:
            mybar.progress(0.9, text="Merging new data and saving to CSV...")
            new_df = pd.concat(new_data)
            new_df['dateTimeUtc'] = pd.to_datetime(new_df['dateTimeUtc']).dt.tz_localize(None)
            df = pd.concat([df, new_df])
            df = df.drop_duplicates(subset=['dateTimeUtc', 'cnecName'])
            df.to_csv(csv_filename, index=False)
            st.success(f"Updated {csv_filename} with missing data.")

        mybar.progress(1.0, text="Done!")
        mask = (df['dateTimeUtc'] >= start_ts) & (df['dateTimeUtc'] <= end_ts)
        return df.loc[mask].reset_index(drop=True)

    # If file does not exist, download all data
    mybar.progress(0.1, text="Downloading all data...")
    url = (f"https://publicationtool.jao.eu/nordic/api/data/fbDomainShadowPrice?Filter=%7B%22NonRedundant%22%3Atrue%7D&"
           f"Skip=0&Take=10000&FromUtc={start_str}.000Z&ToUtc={end_str}.000Z")
    res = requests.api.get(url)
    res_decoded = res.content.decode('utf-8')
    response = json.loads(res_decoded)
    df = pd.DataFrame(response['data'])
    df['dateTimeUtc'] = pd.to_datetime(df['dateTimeUtc']).dt.tz_localize(None)
    total_len = response['totalRowsWithFilter']
    skip = 10000
    while total_len > skip:
        mybar.progress(min(0.9, skip/total_len), text=f"Downloading data... ({skip}/{total_len})")
        url = (f"https://publicationtool.jao.eu/nordic/api/data/fbDomainShadowPrice?Filter=%7B%22NonRedundant%22%3Atrue%7D&"
               f"Skip={skip}&Take=10000&FromUtc={start_str}.000Z&ToUtc={end_str}.000Z")
        res = requests.api.get(url)
        res_decoded = res.content.decode('utf-8')
        response = json.loads(res_decoded)
        temp_df = pd.DataFrame(response['data'])
        temp_df['dateTimeUtc'] = pd.to_datetime(temp_df['dateTimeUtc']).dt.tz_localize(None)
        df = pd.concat([df, temp_df])
        skip += 10000
    df.to_csv(csv_filename, index=False)
    mybar.progress(1.0, text="Saved all data to CSV.")
    st.success(f"Saved all data to {csv_filename}")
    return df

data = get_puto_data(start_date, end_date)
data['dateTimeUtc'] = pd.to_datetime(data['dateTimeUtc']).dt.tz_localize(None)
data.set_index('dateTimeUtc', inplace=True)

# Add multi-select filter for 'tso'
tso_filter = st.sidebar.multiselect('Select TSO(s)', data['tso'].unique())

# Filter data based on selected 'tso'
if len(tso_filter) > 0:
    data = data[data['tso'].isin(tso_filter)]
#st.dataframe(data)

# combine biddingZoneFrom and biddingZoneTo to create a new column 'AreaFromTo'
data['AreaFromTo'] = data['biddingZoneFrom'] + ' - ' + data['biddingZoneTo']

tab1, tab2 = st.tabs(['Shadow price', 'Data for selected CNECs'],)
with tab1:
    shadow_prices = data.groupby(["cnecName"])["shadowPrice"].sum().reset_index()

    #shadow_prices.set_index('dateTimeUtc', inplace=True)
    #filt
    shadow_prices = shadow_prices[shadow_prices['shadowPrice']>0.01]

    # Do the same, but group by areaFromTo
    area_shadow_prices = data.groupby(["AreaFromTo"])["shadowPrice"].sum().reset_index()
    #area_shadow_prices.set_index('dateTimeUtc', inplace=True)

    tso_shadow_prices = data.groupby(["tso"])["shadowPrice"].sum().reset_index()
    #tso_shadow_prices.set_index('dateTimeUtc', inplace=True)



    with chart_container(data, ["Chart 📈", "Data 📄", "Download 📁"], ["CSV"]):
        shadow_prices = shadow_prices.sort_values('shadowPrice', ascending=True)
        #fig = px.bar(shadow_prices, y='cnecName', x='shadowPrice', orientation='h', hover_data=[shadow_prices.index],
                   # title="Cumulative shadow prices for each CNE", height=1000)
        
        

        #st.plotly_chart(fig, use_container_width=True)
        
        fig_area = px.bar(area_shadow_prices, x='AreaFromTo', y='shadowPrice', orientation='v',
                    title="Cumulative shadow prices for each Area pair")
        fig_area.update_layout(xaxis={'categoryorder':'total descending'}, yaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_area, use_container_width=True)

        tso_shadow_prices = tso_shadow_prices.sort_index()
        fig_tso = px.bar(tso_shadow_prices, y='tso', x='shadowPrice', orientation='h',
                    title="Cumulative shadow prices for each TSO")
        st.plotly_chart(fig_tso, use_container_width=True)

        #plot each cnec shadow price
        cnecs = shadow_prices['cnecName'].unique()
        fig2 = go.Figure()
        for cnec in cnecs:
            temp_data = shadow_prices[shadow_prices['cnecName'] == cnec]
        
            fig2.add_trace(go.Scatter(x=temp_data.index, y=temp_data['shadowPrice'], mode='markers+lines', name=cnec,
                                    connectgaps=False))
        
        fig2.update_layout(dict(yaxis_title='Shadow Price €/MW', xaxis_title='Time', legend_title="CNEC name"
                                ,hovermode="x unified"))
        fig2.update_layout(xaxis={'categoryorder':'total descending'}, yaxis={'categoryorder':'total descending'})
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
            for col in col_filter:
                fig3.add_trace(go.Scatter(x=temp_data.index, y=temp_data[col], mode='lines', name=f"{cnec} {col}",
                                        connectgaps=False))
        fig3.update_layout(dict(yaxis_title='Value', xaxis_title='Time', legend_title="CNEC name and column",
                                hovermode="x unified"))
        st.plotly_chart(fig3, use_container_width=True)
