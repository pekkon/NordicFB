import streamlit as st
import pandas as pd
from streamlit_extras.mention import mention

import datetime

def get_general_layout(start=None):
    # Start of the page
    end = datetime.datetime.now() + datetime.timedelta(days=1)
    st.sidebar.subheader("Choose date window 📆")
    if start is not None:
        default = datetime.date(2024, 10, 29)
    else:
        if 'current_start_date' in st.session_state:
            default = st.session_state['current_start_date']
        else:
            default = datetime.date(2024, 10, 29)

    # Setup date inputs so user can select their desired date range but make sure they don't non-feasible date ranges
    # start_date cannot go over end_date, and we need to save end_date to session_state in case user changed end_date

    if 'current_end_date' not in st.session_state:
        start_date = st.sidebar.date_input("Date start", default,
                                           min_value=datetime.date(2024, 10, 29),
                                           max_value=end)
        end_date = st.sidebar.date_input("Date end", end,
                                         min_value=start_date,
                                         max_value=end, key='current_end_date')
    else:
        start_date = st.sidebar.date_input("Date start", default,
                                           min_value=datetime.date(2024, 10, 29),
                                           max_value=st.session_state['current_end_date'])
        end_date = st.sidebar.date_input("Date end", st.session_state['current_end_date'],
                                         min_value=start_date,
                                         max_value=end, key='current_end_date')
    if start is None:
        st.session_state['current_start_date'] = start_date
    #aggregation_selection_selection = st.sidebar.radio('Choose aggregation level 🕑', ['Hour', 'Day', 'Week', 'Month'])

    # Add contact info and other information to the end of sidebar
    with st.sidebar:
        sidebar_contact_info()

    return start_date, end_date#, aggregation_selection_selection


def sidebar_contact_info():
    # Setup sidebar contact and other info

    st.subheader("Contact:")
    mention(
        label="LinkedIn",
        icon="💼",
        url="https://www.linkedin.com/in/pekko-niemi/"
    )
    mention(
        label="X",
        icon="‍☠️",
        url="https://X.com/PekkoNiemi"
    )
    mention(
        label="Source code",
        icon="github",
        url="https://github.com/pekkon/EnergiaDataApp"
    )
    st.markdown('Data sources:  \n[JAO Publication tool](https://publicationtool.jao.eu/nordic/api)')


