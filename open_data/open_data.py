from pyaxis import pyaxis
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st


URL = "https://podatki.nijz.si/DB/NIJZ%20podatkovni%20portal/8%20Kazalniki%20obvladovanja%20kroni%C4%8Dnih%20bolezni/01%20Sladkorna%20bolezen/01%20Prevalenca%20in%20incidenca/80101009.px"


st.set_page_config(page_title="MedBrief open data", layout="wide")
st.title("Diabetes prevalence in Slovenia")
st.caption("Choose gender and age group. Education level is optional.")

# Fetch once per browser session; changing a filter reuses the loaded data.
if "diabetes_px" not in st.session_state:
    with st.spinner("Loading PC-Axis data..."):
        st.session_state["diabetes_px"] = pyaxis.parse(URL, encoding='cp1250')
px = st.session_state["diabetes_px"]

#print(px['DATA'])

df = px['DATA']

df= df.rename(columns = {'DATA':'Delež oseb s diabetesom' })

df['Leto'] = pd.to_numeric(df['Leto'],errors='coerce')

df['Delež oseb s diabetesom'] = pd.to_numeric(df['Delež oseb s diabetesom'], errors = 'coerce')

#print(df.dtypes)

moski = df[df['Spol'] == 'Moški']
zenske = df[df['Spol'] == 'Ženske']

#print(moski)
#print(zenske)


def izbira_po_spolu_in_starosti(df, Spol, Starost , Izobrazba = None):

    izbrani_spol = df['Spol']==Spol #pretvori ovo u bool(true/false)
    izbrana_starost = df['Starost'] == Starost 

    if Izobrazba is not None:
        izbrano = df[izbrani_spol & izbrana_starost & (df['Izobrazba']==Izobrazba)] # proveri svaki uslov da je true, kao df[true, true, true] i onda vrati
    else:
        izbrano =  df[izbrani_spol & izbrana_starost] #izabere iz df samo tabele koje je vratilo kao true

    return izbrano     

    


def draw_graph(df):
    value_column = "Delež oseb s diabetesom"
    fig, ax = plt.subplots()

    # Each group contains only the rows for one education level.
    for education_level, group_data in df.groupby("Izobrazba"):
        # Sort before connecting points so the line follows time forward.
        group_data = group_data.sort_values("Leto")
        ax.plot(group_data["Leto"], group_data[value_column],
                marker="o", label=education_level)

    ax.set_xlabel("Year")
    ax.set_ylabel("Share of people with diabetes (%)")
    ax.set_title("Diabetes prevalence by education level")
    # Match the line colors to the education levels shown in the chart.
    ax.legend(title="Education level")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig


# Use the source's category names so the filter receives matching values.
selected_sex = st.selectbox("Gender", df["Spol"].dropna().unique(),
                            index=None, placeholder="Choose gender", key="diabetes_sex")
selected_age = st.selectbox("Age group", df["Starost"].dropna().unique(),
                            index=None, placeholder="Choose age group", key="diabetes_age")
selected_education = st.selectbox("Education level (optional)", df["Izobrazba"].dropna().unique(),
                                  index=None, placeholder="All education levels",
                                  key="diabetes_education")

st.markdown("Source: [NIJZ dataset on OPSI](https://podatki.gov.si/dataset/nijz80101009)")

# Both required choices must exist before filtering or drawing a graph.
if selected_sex is None or selected_age is None:
    st.info("Choose gender and age group to display the data.")
    st.stop()

selected_data = izbira_po_spolu_in_starosti(df, selected_sex, selected_age, selected_education)
if selected_data.empty:
    st.info("No data is available for this combination.")
else:
    # Pass the same filtered data to the chart and the table for comparison.
    figure = draw_graph(selected_data)
    st.pyplot(figure, alt="Diabetes prevalence by year and education level for the selected group.")
    plt.close(figure)
    st.dataframe(selected_data.sort_values(["Izobrazba", "Leto"]), hide_index=True,
                 alt="Values used in the diabetes prevalence chart.")
