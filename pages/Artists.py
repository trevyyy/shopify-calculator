import streamlit as st
import json
import time

if 'artists' not in st.session_state:
    with open('artists.json') as j:
        st.session_state['artists'] = json.load(j)

new_data = []

if st.button('➕ Add'):
    st.session_state['artists'].append({'name': '', 'items': ''})

for i, a in enumerate(st.session_state['artists']):
    name = st.text_input('Name', value=a['name'], key=f'0-{i}-{a}')
    items = st.text_area('Prints', value='\n'.join(a['items']), help='Add each print on a new line', key=f'1-{i}-{a}')
    new_data.append({'name': name, 'items': [i.strip() for i in items.splitlines() if i.strip()]})
    st.write('---')

if st.button('Save'):
    new_data = [n for n in new_data if n['name']]
    with open('artists.json', 'w') as j:
        json.dump(new_data, j)
    st.success('Saved')
    with open('artists.json') as j:
        st.session_state['artists'] = json.load(j)
    time.sleep(2)
    st.experimental_rerun()
