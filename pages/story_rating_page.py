import streamlit as st
# Importing the REQUIRED function from the processor file
from ai.story_processor import analyze_story_rating 
import json

def show():
    # Set initial state for analysis completion and image rendering
    if "story_analysed" not in st.session_state:
        st.session_state["story_analysed"] = False
        st.session_state["story_result"] = None
        st.session_state["story_image_urls"] = [] 

    st.markdown("### 🎙️ SG Voice: Story Ranker")
    st.markdown("---")
    st.markdown(
    """Analyze and score a **Story** from the PDF document and rank it based on three critical criteria: Impact/Outcome, Issue/Challenge clarity, and Action Steps taken.  
    <span style="color:#1E90FF;"><b>Input: From MI stories csv choose Title, Pdf columns</b></span>
    """,unsafe_allow_html=True
    )
    
    # --- Input Section ---
    col_input, col_model = st.columns([3, 1])

    with col_input:
        st.markdown("**Enter Story Details**")
        
        # 1. Title (Mandatory)
        title = st.text_input("1. Title", key="story_title_input")
        
        # 2. PDF Link (Mandatory)
        pdf_url = st.text_input("2. PDF Link (URL)", key="story_pdf_input",
                                placeholder="e.g., https://example.com/story_document.pdf")

        # 3. Image Links (Optional for AI, but stored for rendering)
        image_url_input = st.text_area("3. Image Links from Images column - Optional", key="story_image_input", 
                                  height=70,
                                  placeholder="e.g., link1.jpg | link2.png | link3.jpeg")
        
        # 4. Story Content (Re-added as Optional)
        content = st.text_area("4. Content - Optional", key="story_content_input", height=150, 
                               placeholder="Enter any additional or corrected text content here. This supplements the PDF extraction.")
    
    with col_model:
        st.markdown("<br><br>", unsafe_allow_html=True) 
        model_choice = st.selectbox(
            "Select AI Model:",
            ["Gemini-2.5-Flash", "ChatGPT-4o", "Claude-3-Sonnet"], 
            key="story_model_choice"
        )
        
        if st.button("✨ Rate Story", use_container_width=True, key="story_rate_btn"):
            if not title.strip() or not pdf_url.strip():
                st.warning("🚨 **Title** and **PDF Link** are mandatory to proceed.")
            else:
                # Process the multiple image links
                all_image_urls = [url.strip() for url in image_url_input.split('|') if url.strip()]
                primary_image_for_ai = all_image_urls[0] if all_image_urls else ""

                # Clear previous state
                st.session_state["story_analysed"] = False
                st.session_state["story_result"] = None
                st.session_state["story_image_urls"] = all_image_urls 

                # Call the processor function, passing the optional 'content'
                with st.spinner(f"Downloading PDF, extracting text, and rating story using {model_choice}..."):
                    result = analyze_story_rating(title, pdf_url, primary_image_for_ai, model_choice, content)
                    st.session_state["story_result"] = result
                    st.session_state["story_analysed"] = True
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    
    # --- Detailed Output Section ---
    
    if st.session_state.get("story_analysed") and st.session_state["story_result"]:
        result = st.session_state["story_result"]
        
        if "error" in result:
            st.error(f"❌ Analysis Error: {result['error']}")
            
            # Show additional debug info if available
            if "partial_response" in result:
                with st.expander("🔍 Debug: Partial Response Received"):
                    st.json(result['partial_response'])
                    st.warning("The model returned incomplete data. Try running the analysis again or switch to a different model.")
            
            if "raw_response" in result:
                with st.expander("🔍 Debug: Raw Model Response"):
                    st.code(result['raw_response'], language="text")
        else:
            # 1. Image Preview and Summary Column
            st.markdown("### 🖼️ Story Snapshot & Composite Score")
            
            doc_lang = result.get('document_language', 'N/A')
            st.markdown(f"**Document Language Detected:** <span style='background-color:#ffe0b2; color:black; padding:3px 8px; border-radius:5px;'>{doc_lang}</span>", unsafe_allow_html=True)
            st.markdown("---")

            score_summary_col, image_display_col = st.columns([1.2, 2]) 
            
            # --- Composite Score and Summary Block (In the Left Column) ---
            with score_summary_col:
                composite_score = result.get('composite_score', 'N/A')
                tier = result.get('tier', 'Unknown')
                
                st.markdown(f"**Composite Score:** <span style='font-size: 2.5em; font-weight: 700; color:#4facfe;'>{composite_score}</span>", unsafe_allow_html=True)
                
                # Tier Styles
                tier_style = {
                    "Excellent": "background-color:#2ecc71; color:white; padding:5px 10px; border-radius:5px; font-weight:bold;",
                    "Good": "background-color:#f1c40f; color:black; padding:5px 10px; border-radius:5px; font-weight:bold;",
                    "Developing": "background-color:#3498db; color:white; padding:5px 10px; border-radius:5px; font-weight:bold;",
                    "Needs Improvement": "background-color:#e74c3c; color:white; padding:5px 10px; border-radius:5px; font-weight:bold;",
                }.get(tier, "background-color:#e0e0e0; padding:5px 10px; border-radius:5px;")

                st.markdown(f"**Overall Tier:** <span style='{tier_style}'>{tier}</span>", unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("**Overall Summary:**")
                st.info(result.get('overall_summary', 'No summary provided.'))


            # --- Image Rendering Block (In the Right Column) ---
            with image_display_col:
                image_urls = st.session_state.get("story_image_urls", [])
                
                if image_urls:
                    st.markdown("**Story Images**")
                    
                    num_images = len(image_urls)
                    num_cols_in_row = min(num_images, 2) 
                    
                    failed_images = []
                    
                    for row_start_index in range(0, num_images, 2):
                        row_cols = st.columns(num_cols_in_row) 
                        
                        for col_index in range(num_cols_in_row):
                            img_index = row_start_index + col_index
                            if img_index < num_images:
                                url = image_urls[img_index]
                                with row_cols[col_index]:
                                    try:
                                        st.image(url, 
                                                 caption=f"Image {img_index + 1}", 
                                                 use_container_width=True)
                                    except Exception as e:
                                        failed_images.append((url, str(e)))
                                        st.warning(f"Image {img_index + 1} failed to load.", icon="⚠️")

                    if failed_images:
                        st.error(f"Note: {len(failed_images)} image(s) could not be rendered.")
                else:
                    st.info("No image link provided.")
            
            st.markdown("---") 

            # 3. Score Breakdown Table
            st.markdown("### 📋 Score Breakdown and Justification")
            
            breakdown_data = [
                {
                    "Criterion": "Impact & Outcome",
                    "Score": f"{result.get('impact_and_outcome_score', 'N/A')}",
                    "Justification": result.get('impact_justification', 'No justification.'),
                },
                {
                    "Criterion": "Issue & Challenge",
                    "Score": f"{result.get('issue_and_challenge_score', 'N/A')}",
                    "Justification": result.get('issue_justification', 'No justification.'),
                },
                {
                    "Criterion": "Action Steps",
                    "Score": f"{result.get('action_steps_score', 'N/A')}",
                    "Justification": result.get('action_justification', 'No justification.'),
                },
            ]

            st.dataframe(
                breakdown_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Criterion": st.column_config.Column("Criterion", width="small"),
                    "Score": st.column_config.Column("Score", width="small"),
                    "Justification": st.column_config.Column("Justification", width="large"),
                }
            )