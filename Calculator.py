import streamlit as st
import pandas as pd
import re
import json
from thefuzz import fuzz

st.set_page_config(page_icon='🎨')

with open('artists.json') as j:
    ARTISTS = json.load(j)


def parse_id(product_id):
    entities = {
        'measurement': re.findall('[0-9]+x[0-9]+-inch', product_id)[0],
        'insert': 'insert' in product_id,
        'sticker': 'sticker' in product_id,
        'poster': 'poster' in product_id
    }
    if entities['poster']:
        if 'flat' in product_id:
            entities['framed'] = False
            entities['color'] = None
        else:
            entities['framed'] = True
            entities['color'] = re.findall('_[a-z]+_wood', product_id)[0]
    else:
        entities['framed'] = False
        entities['color'] = None
    return entities


def split_name(product_listing):
    match = re.search('[0-9]+"', product_listing)
    if match:
        name = product_listing[:match.start(0)]
        name = name.strip('- ')
        return name
    return None


@st.cache_data
def convert_df(df):
    return df.to_csv().encode('utf-8')


artist_data = st.selectbox('Artist', [*ARTISTS], format_func=lambda a: a['name'])
shopify_file = st.file_uploader('Shopify file', type='csv')
if shopify_file:
    shopify_df = pd.read_csv(shopify_file, usecols=['Order', 'Product', 'Variant', 'Gross sales'])
    shopify_df.rename(columns={'Gross sales': 'Sales'}, inplace=True)
    shopify_df.fillna('', inplace=True)
    shopify_df['Size'] = shopify_df['Variant'].apply(lambda n: n.split('/')[0].strip() if '/' in n else n)
    shopify_df['Frame'] = shopify_df['Variant'].apply(lambda n: n.split('/')[1].strip() if '/' in n else n)
    shopify_df = shopify_df[['Order', 'Product', 'Size', 'Frame', 'Sales']]
    if 'shopify_df' not in st.session_state:
        st.session_state['shopify_df'] = shopify_df

if 'shopify_df' in st.session_state:
    st.dataframe(st.session_state['shopify_df'], use_container_width=True)
    st.write('---')

    fuzzy_matches = []
    exact_matches = []
    for item in artist_data['items']:
        exact_match_found = False
        temp_matches = []
        for prod in st.session_state['shopify_df']['Product'].unique():
            if prod == item:
                exact_match_found = True
                exact_matches.append(prod)
            elif 90 < fuzz.ratio(item, prod) < 100:
                temp_matches.append([item, prod])
        if not exact_match_found:
            fuzzy_matches += temp_matches
    for m in exact_matches:
        for i, f in enumerate(fuzzy_matches):
            if m in f:
                fuzzy_matches.pop(i)
    if fuzzy_matches:
        for f in fuzzy_matches:
            st.info(f'Check {artist_data["name"]}\'s product listings: did you mean **"{f[1]}"** instead of **"{f[0]}"**?')

    person_df = st.session_state['shopify_df'][st.session_state['shopify_df']['Product'].isin(artist_data['items'])]
    person_df['Percentage'] = [artist_data["unframed"] if f == 'Unframed' else artist_data["framed"] for f in person_df['Frame']]
    person_df['Cut'] = person_df['Sales'] * person_df['Percentage']

    st.write(f'No. of orders: **{len(st.session_state["shopify_df"])}**')
    st.write(f'No. of orders that included print by artist: **:red[{len(person_df["Order"].unique())}]**')
    st.write(f'Total owed to artist: **:red[£{round(person_df["Cut"].sum(), 2)}]**')

    st.dataframe(person_df, use_container_width=True)

    csv = convert_df(person_df)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name='invoice.csv',
        mime='text/csv',
    )
