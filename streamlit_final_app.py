import streamlit as st
from fetch_case_data_and_summarize import IKApi, query_ai_model  

ikapi = IKApi(maxpages=5)

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
            for docid in doc_ids[:2]:  
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
