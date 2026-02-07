import streamlit as st
import requests
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.markdown(open("cyberpunk.css").read(), unsafe_allow_html=True)

st.title("🎧 AudioInsight")

file = st.file_uploader("Upload MP3", type=["mp3", "wav"])

if file:
    response = requests.post(
        "http://localhost:8000/analyze",
        files={"file": file}
    ).json()

    st.metric("🎵 BPM", response["bpm"])
    st.metric("🎼 Key", response["key"])

    y, sr = response["waveform"]
    fig, ax = plt.subplots()
    ax.plot(y)
    st.pyplot(fig)

    spec = np.array(response["spectrogram"])
    fig, ax = plt.subplots()
    ax.imshow(spec, aspect="auto", origin="lower")
    st.pyplot(fig)
