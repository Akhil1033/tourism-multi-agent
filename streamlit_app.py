import streamlit as st
from app import tourism_parent_agent


st.set_page_config(
    page_title="Tourism Multi-Agent AI",
    page_icon="🌍",
    layout="centered",
)

st.title("🌍 Tourism Multi-Agent AI System")
st.write(
    "Ask about a place you want to visit, and I'll tell you the weather, "
    "tourist places, or both – using real APIs."
)

st.markdown("___")


default_query = "I'm going to go to Bangalore, what is the temperature there? And what are the places I can visit?"

user_query = st.text_area(
    "📝 Type your travel query here:",
    value=default_query,
    height=120,
)

if st.button("✨ Plan my trip"):
    if not user_query.strip():
        st.warning("Please type something about where you want to go.")
    else:
        with st.spinner("Thinking using multiple agents..."):
            try:
                reply = tourism_parent_agent(user_query)
            except Exception as e:
                reply = f"Something went wrong while processing your query: {e}"

        st.markdown("### ✅ Response")
        # Respect line breaks from the agent
        st.markdown(reply.replace("\n", "  \n"))
        
st.markdown("___")
st.caption("Powered by Nominatim, Open-Meteo, Overpass API, and a custom multi-agent system.")
