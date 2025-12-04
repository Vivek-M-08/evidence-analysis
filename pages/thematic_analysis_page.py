import streamlit as st
from ai.thematic_processor import analyze_thematic_challenge 
import json

def show():
    # Set session state for analysis tracking if not already present
    if "thematic_analysed" not in st.session_state:
        st.session_state["thematic_analysed"] = False
        st.session_state["thematic_result"] = None
        st.session_state["thematic_input_challenges"] = [] # Store processed list of challenges

    st.markdown("### 🎙️ SG Voice: Thematic Analysis")
    st.markdown("---")
    st.markdown(
    """Classify raw text challenges into pre-defined themes and detect PII (Personal Identifiable Information).  
    <span style="color:#1E90FF;"><b>Input: From Chaupal/Chavadi csv choose Challenges column</b></span>
    """,unsafe_allow_html=True
    )
    
    # Define layout columns
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("**Enter Challenges**")
        input_text = st.text_area(
            "Paste a list of educational challenge statements (separated by the pipe '|' character).",
            key="thematic_input_text",
            height=300,
            placeholder="e.g., Due to poor financial condition, the girl is not able to study | Raj Kumar's daughter from ward 3 cannot go to school due to lack of Aadhaar | School infrastructure is poor",
            label_visibility="collapsed"
        )
        
        # --- AI Model Selection and Analysis Button ---
        st.markdown("<br>", unsafe_allow_html=True)
        btn_col1, btn_col2 = st.columns([1, 2])

        with btn_col1:
            model_choice = st.selectbox(
                "Select AI Model:",
                ["Gemini-2.5-Flash", "ChatGPT-4o-Mini", "Claude-4.5-Sonnet"],
                key="thematic_model_choice"
            )

        with btn_col2:
            st.markdown("<br>", unsafe_allow_html=True) # Align button visually
            if st.button("🧠 Analyze Challenges", use_container_width=True, key="thematic_analyze_btn"):
                if not input_text.strip():
                    st.warning("Please enter challenge statements to analyze.")
                else:
                    # Split input text by '|' and strip whitespace
                    challenges = [c.strip() for c in input_text.split('|') if c.strip()]
                    
                    if not challenges:
                        st.warning("The input text must contain at least one valid challenge statement.")
                        st.session_state["thematic_analysed"] = False
                    else:
                        # Join the challenges back with newlines for the processor function 
                        # which is designed to handle newline-separated input for batching.
                        input_for_processor = "\n".join(challenges)
                        
                        # Store the processed list of challenges for later table display
                        st.session_state["thematic_input_challenges"] = challenges
                        st.session_state["thematic_result"] = None
                        
                        with st.spinner(f"Analyzing text using {model_choice}..."):
                            result = analyze_thematic_challenge(input_for_processor, model_choice)
                            st.session_state["thematic_result"] = result
                            st.session_state["thematic_analysed"] = True
                            st.rerun() # Rerun to display results

    with col2:
        # --- Output Summary ---
        st.markdown("**Output Summary**")
        if st.session_state.get("thematic_analysed"):
            result = st.session_state["thematic_result"]
            
            if "error" in result:
                st.error(f"❌ Analysis Error: {result['error']}")
            else:
                st.success("Analysis Complete!")
                
                # Calculate summary metrics
                classified_data = result.get("classified_data", [])
                total_entries = len(classified_data)
                pii_count = sum(1 for item in classified_data if item.get("pii_flag"))
                
                st.markdown(f"* **Total Entries Processed:** **{total_entries}**")
                st.markdown(f"* **PII Detected:** **{pii_count}** entries")

                # Show a simple theme count
                theme_counts = {}
                for item in classified_data:
                    theme_name = item.get("theme_name", "N/A")
                    theme_counts[theme_name] = theme_counts.get(theme_name, 0) + 1
                
                st.markdown("**Top Themes:**")
                for theme, count in sorted(theme_counts.items(), key=lambda item: item[1], reverse=True)[:3]:
                    st.markdown(f"- {theme}: {count}")

        else:
            st.info("Results will appear here after analysis.")

    st.markdown("---")
    
    # --- Detailed Output Table ---
    if st.session_state.get("thematic_analysed") and st.session_state["thematic_result"].get("classified_data"):
        st.markdown("### 📋 Detailed Classification Results")
        
        # --- Use stored processed challenges list ---
        challenges = st.session_state.get("thematic_input_challenges", [])
        classified = st.session_state["thematic_result"]["classified_data"]

        data_to_show = []
        
        # Ensure challenges and classifications align
        max_len = max(len(challenges), len(classified))
        
        for i in range(max_len):
            challenge = challenges[i] if i < len(challenges) else "N/A (Input Missing)"
            classification = classified[i] if i < len(classified) else {}
            
            pii_flag = classification.get("pii_flag")
            pii_display = "⚠️ YES" if pii_flag else ("✅ NO" if pii_flag is not None else "N/A")
            
            data_to_show.append({
                "Challenge Statement": challenge,
                "Theme ID": classification.get("theme_id", "N/A"),
                "Theme Name": classification.get("theme_name", "N/A"),
                "PII Detected": pii_display
            })

        st.dataframe(
            data_to_show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Challenge Statement": st.column_config.Column("Challenge Statement", width="large"),
                "PII Detected": st.column_config.Column("PII Detected", width="small")
            }
        )


