import streamlit as st
from fetch_case_data_and_summarize import IKApi, query_ai_model
import streamlit_authenticator as stauth
import json

passwords = ["admin123", "password123"]
hashed_passwords = stauth.Hasher(passwords).hash(passwords)

# Correct structure for credentials
user_data = {
    "usernames": {
        "admin": {
            "name": "Admin User",
            "password": hashed_passwords[0],
        },
        "john_doe": {
            "name": "Ahil",
            "password": hashed_passwords[1],
        },
    }
}

pending_users = {}

# Functions for user management
def register_user(username, password):
    if username in user_data:
        return False, "Username already exists."
    pending_users[username] = {"password": password}
    return True, "Registration successful. Awaiting admin approval."

def approve_user(username):
    if username in pending_users:
        user_data[username] = pending_users.pop(username)
        user_data[username]["approved"] = True
        return True, f"User {username} approved."
    return False, "No such user in pending list."

def is_user_approved(username):
    return user_data.get(username, {}).get("approved", False)

# Fetch Case Data Instance
ikapi = IKApi(maxpages=5)

# Login/Registration UI
st.sidebar.title("Login/Register")
authenticator = stauth.Authenticate(
    credentials=user_data, cookie_name="case_app", key="abcdef", cookie_expiry_days=1
)

name, authentication_status, username = authenticator.login("Login", "sidebar")

# Handle Login
if authentication_status:
    if username == "admin":
        st.sidebar.subheader("Admin Panel")
        if st.sidebar.checkbox("View Pending Users"):
            st.write("Pending User Approvals:")
            for user in pending_users.keys():
                st.write(user)
                if st.button(f"Approve {user}"):
                    success, message = approve_user(user)
                    st.success(message) if success else st.error(message)
    else:
        if is_user_approved(username):
            st.sidebar.success(f"Welcome, {username}")
            # Main App Logic
            st.title("Legal Case Analysis Assistant")
            st.markdown("This app provides detailed insights from legal case summaries.")

            query = st.text_input("Enter your legal query (e.g., 'road accident cases'):")
            if st.button("Analyze"):
                if not query.strip():
                    st.warning("Please enter a valid query.")
                else:
                    st.info("Fetching related cases...")
                    doc_ids = ikapi.fetch_all_docs(query)

                    if not doc_ids:
                        st.error("No related documents found for your query.")
                    else:
                        st.success(f"Found {len(doc_ids)} related documents. Processing summaries...")

                        all_summaries = []
                        for docid in doc_ids[:2]:  # Process only 2 documents for demonstration
                            case_details = ikapi.fetch_doc(docid)

                            if not case_details:
                                st.warning(f"Failed to fetch details for document ID: {docid}")
                                continue

                            title = case_details.get("title", "No Title")
                            main_text = case_details.get("doc", "")
                            cleaned_text = ikapi.clean_text(main_text)
                            chunks = list(ikapi.split_text_into_chunks(cleaned_text))
                            summaries = []

                            for chunk in chunks:
                                summary = ikapi.summarize(chunk)
                                if summary:
                                    summaries.append(summary)

                            final_summary = " ".join(summaries)
                            all_summaries.append(f"Title: {title}\nSummary: {final_summary}")

                        combined_summary = "\n\n".join(all_summaries)
                        st.subheader("Summarized Case Details")
                        st.text_area("Summaries", combined_summary, height=300)

                        st.info("Generating insights from summaries...")
                        insights = query_ai_model(query, combined_summary)
                        st.subheader("AI Insights and Analysis")
                        st.write(insights)
        else:
            st.sidebar.error("Your account is pending approval. Please wait for admin approval.")
elif authentication_status == False:
    st.sidebar.error("Username or password is incorrect")
elif authentication_status is None:
    st.sidebar.info("Please log in to access the app")

# Registration Logic
if st.sidebar.checkbox("Register"):
    st.sidebar.subheader("Register New Account")
    new_username = st.sidebar.text_input("Username", key="register_username")
    new_password = st.sidebar.text_input("Password", type="password", key="register_password")
    if st.sidebar.button("Register"):
        success, message = register_user(new_username, new_password)
        st.sidebar.success(message) if success else st.sidebar.error(message)
