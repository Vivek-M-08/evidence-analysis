# evidence_analysis_page.py (MODIFIED)
import streamlit as st
from ai.process_evidence import analyze_evidence

def show():
    # NOTE: The header (Title, Reports, Logout) is now handled in app.py

    # An empty break line added (Removed the styled <hr> as it's now in app.py)
    # st.markdown("<br>", unsafe_allow_html=True) 

    # Define layout columns
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

    # Column 1: Enter 7 Questions
    with col1:
        st.markdown("<div style='font-size:24px; font-weight:600;'>📋 Enter Questions</div>", unsafe_allow_html=True)
        question_inputs = []
        # Use st.form for a better grouping of inputs if desired, but maintaining original logic for consistency
        for i in range(1, 8):
            q = st.text_area(f"{i}.", key=f"question_{i}",  height=100)
            question_inputs.append(q)

    # Column 2: Evidence Link Input + Analyse Button
    with col2:
        st.markdown("<div style='font-size:24px; font-weight:600;'>🔗 Paste Evidence Link</div>", unsafe_allow_html=True)
        image_url = st.text_area("Image URL", height=150, key="evidence_url_input") # Added key for uniqueness
        default_prompt = """You are an educational evidence validator. Analyse this image as field evidence from a PBL classroom in Bihar, India. Answer the added questions with 'YES' or 'NO', consider all visible elements and context. Explain your reasoning for each answer briefly."""
        prompt_text = st.text_area("Prompt (Editable)", value=default_prompt, height=150, key="evidence_prompt_input") # Added key
        context = prompt_text + "\n\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(question_inputs) if q.strip()])

        if st.button("🔍 Analyse", use_container_width=True, key="evidence_analyse_btn"):
            if not image_url.strip():
                st.warning("Please provide an evidence link.")
            elif not any(q.strip() for q in question_inputs):
                st.warning("Please enter at least one question.")
            else:
                with st.spinner("Analyzing Evidence..."):
                    result = analyze_evidence(image_url, context, use_openai=False)
                    
                    if "error" in result:
                        st.error(f"❌ Error: {result['error']}")
                    else:
                        st.session_state["image_url"] = image_url
                        st.session_state["questions"] = question_inputs
                        st.session_state["ai_result"] = result
                        st.session_state["analysed"] = True

    # Column 3: Image Preview
    with col3:
        st.markdown("<div style='font-size:24px; font-weight:600;'>🖼️ Image Preview</div>", unsafe_allow_html=True)
        if st.session_state.get("analysed", False):
            # Check if image_url exists in state before trying to display
            if st.session_state.get("image_url"):
                st.image(st.session_state["image_url"], width=350)
            else:
                st.warning("Image URL missing from session state.")
        else:
            st.info("Awaiting evidence link and analysis...")

    # Column 4: Output Summary
    with col4:
        st.markdown("<div style='font-size:24px; font-weight:600;'>🧠 Output Summary</div>", unsafe_allow_html=True)
        if st.session_state.get("analysed", False):
            result = st.session_state.get("ai_result", {})
            if result:
                st.markdown(f"**Source:** {result.get('source', 'N/A')}")
                st.markdown("**🟢 Relevance Tag:** " + result.get("relevance", "Unknown"))
                st.markdown("**✅ Answers:** " + ", ".join(result.get("answers", [])))
                st.markdown("**🧠 Reasoning:**")
                for i, reason in enumerate(result.get("reasonings", []), 1):
                    st.markdown(f"{i}. {reason}")
            else:
                st.text("(No AI output found)")
        else:
            st.info("Output will appear after clicking Analyse.")