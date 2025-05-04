from upload_in_KB import UploadInKB
import requests
from dotenv import load_dotenv
import os
import streamlit as st
import json

load_dotenv()

USER_ID="test_user"

class TestRAG:
    def __init__(self) -> None:
        self.upload_in_kb = UploadInKB(USER_ID)
        self.grok_chat_url = "https://api.groq.com/openai/v1/chat/completions"
        self.grok_api_key = os.getenv("GROQ_API_KEY")

    def generate_with_context(self, question: str):

        retrieval_context=self.upload_in_kb.retrieve_relevant_knowledge(question)
        print(type(retrieval_context))
        print(len(retrieval_context))
        print(retrieval_context)
        # join the chunks
        retrieval_json = "\n\n".join(retrieval_context)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Answer the user’s question "
                    "ONLY using the provided CONTEXT. "
                    "If the answer cannot be found in the CONTEXT, respond that the answer is not present in the uploaded document."
                    f"CONTEXT: {json.dumps(retrieval_json)}"
                )
            },
            {
                "role": "user",
                "content": question
            }
        ]

        resp = requests.post(
            self.grok_chat_url,
            headers={
                "Authorization": f"Bearer {self.grok_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0.0,
                #"response_format": {"type": "json_object"}
            }
        )
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print("⛔", resp.status_code, resp.text)
            raise

        content = resp.json()["choices"][0]["message"]["content"]
        return content
        #return json.loads(content)

    def chat(self):
        # Initialize chat history in session state if not present
        if 'history' not in st.session_state:
            st.session_state['history'] = []

        #sidebar
        with st.sidebar:
            st.title('🤖💬 Designing Chatbot')
            st.write("Ask me a question about the uploaded document")

        #chat
        for message in st.session_state['history']:
            role = message["role"]
            if role == "user":
                with st.chat_message('user', avatar="https://cdn-icons-png.flaticon.com/512/5987/5987424.png"):
                    st.markdown(message['content'], unsafe_allow_html=True)
            else:
                with st.chat_message('assistant', avatar="https://pressroom.unitn.it/file/pressroom/styles/immagine_comunicato_stampa_narrow/public/immagini/comunicato/6669/logoperpressroom_0.jpg?itok=H9dmU7Od"):
                    st.markdown(message['content'], unsafe_allow_html=True)

        if prompt := st.chat_input("Answer: "):
            st.session_state['history'].append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="https://cdn-icons-png.flaticon.com/512/5987/5987424.png"):
                st.markdown(prompt, unsafe_allow_html=True)
            with st.chat_message("assistant", avatar="https://pressroom.unitn.it/file/pressroom/styles/immagine_comunicato_stampa_narrow/public/immagini/comunicato/6669/logoperpressroom_0.jpg?itok=H9dmU7Od"):
                message_placeholder = st.empty()
                full_response= self.generate_with_context(prompt)
                message_placeholder.markdown(full_response, unsafe_allow_html=True)
            st.session_state['history'].append({"role": "assistant", "content": full_response})

def get_text_to_upload():
    return """# The Climate Sensitivity Debate: Examining the Scientific Arguments

    ## Introduction

    The concept of climate sensitivity—how much the Earth's average temperature will increase in response to a doubling of atmospheric carbon dioxide (CO2) concentrations—represents one of the most consequential yet contentious parameters in climate science. While there is overwhelming scientific consensus that human activities are causing global warming, the precise magnitude of future warming remains an area of active scientific debate. This parameter carries profound implications for climate policy, adaptation strategies, and our understanding of Earth's complex climate system.

    This document explores the scientific arguments surrounding climate sensitivity, examining the evidence, methodologies, and uncertainties that characterize this critical area of research. By understanding the nuances of this debate, we can better appreciate how science works through disagreement to refine our knowledge and inform decision-making in the face of uncertainty.

    ## The Core Concept: Equilibrium Climate Sensitivity

    Equilibrium Climate Sensitivity (ECS) is formally defined as the global mean surface temperature change that would eventually result from a sustained doubling of atmospheric CO2 concentrations after the climate system reaches equilibrium. This parameter has been studied for decades, with the Intergovernmental Panel on Climate Change (IPCC) most recently estimating the likely range to be between 2.5°C and 4°C in its Sixth Assessment Report, narrowed from previous estimates.

    The debate centers around several key questions:

    1. What is the most accurate value for climate sensitivity?
    2. Why do different estimation methods yield different results?
    3. How do feedbacks in the climate system amplify or dampen the initial warming from CO2?
    4. What are the implications of different sensitivity values for climate projections?

    ## Lines of Evidence

    Scientists approach climate sensitivity through multiple independent lines of evidence:

    ### 1. Paleoclimate Records

    Studying Earth's past climates provides valuable insights into how the planet responded to changes in atmospheric composition and other forcings. Ice cores, ocean sediments, and other geological records allow scientists to reconstruct historical CO2 levels and corresponding temperature changes.

    **Supporting Higher Sensitivity:**
    - Studies of the Last Glacial Maximum (approximately 20,000 years ago) suggest that the substantial temperature differences between ice ages and warmer periods are consistent with moderate to high climate sensitivity.
    - Analysis of the mid-Pliocene warm period (about 3 million years ago) indicates that relatively small differences in CO2 produced significant warming, suggesting higher sensitivity.

    **Supporting Lower Sensitivity:**
    - Some analyses of Pleistocene glacial cycles suggest that when accounting for all forcing factors, the inferred sensitivity may be lower than models predict.
    - Refinements in paleotemperature reconstructions have occasionally revised estimates downward.

    ### 2. Observational Record

    Modern instrumental measurements of temperature, ocean heat content, and radiative fluxes provide another crucial line of evidence.

    **Supporting Higher Sensitivity:**
    - The observed warming pattern (more pronounced at the poles, more warming at night than day) aligns with predictions from models with higher sensitivity.
    - Studies of energy imbalance in Earth's radiative budget suggest substantial retained heat consistent with higher sensitivity.

    **Supporting Lower Sensitivity:**
    - Some studies using simple energy balance models applied to the instrumental record (especially from the mid-20th century to present) have yielded lower sensitivity values.
    - Analysis of the "hiatus" period (slower surface warming from roughly 1998-2012) was cited by some researchers as evidence for lower sensitivity, though this interpretation has been contested.

    ### 3. Climate Models

    General Circulation Models (GCMs) and Earth System Models (ESMs) simulate the physical processes of the atmosphere, oceans, land, and ice to estimate climate sensitivity.

    **Supporting Higher Sensitivity:**
    - Most comprehensive climate models in the Coupled Model Intercomparison Project Phase 6 (CMIP6) show sensitivity values in the 2.5-5°C range, with several exceeding 5°C.
    - Models that more accurately reproduce observed climate features often show moderate to high sensitivity.

    **Supporting Lower Sensitivity:**
    - Some researchers argue that climate models may overestimate sensitivity by not properly accounting for certain negative feedbacks or by misrepresenting cloud processes.
    - Models with lower sensitivity values still reproduce many aspects of observed climate change.

    ## The Key Feedbacks Debate

    Much of the sensitivity debate revolves around climate feedbacks—processes that either amplify (positive feedbacks) or diminish (negative feedbacks) the initial warming from increased CO2. The primary feedbacks under discussion include:

    ### 1. Water Vapor Feedback

    As the atmosphere warms, it can hold more water vapor (itself a potent greenhouse gas), amplifying the initial warming.

    **Scientific Consensus:** This is a strong positive feedback that roughly doubles the warming from CO2 alone. This feedback is well-understood and rarely contested.

    ### 2. Cloud Feedbacks

    Changes in cloud amount, altitude, and properties represent the largest source of uncertainty in climate sensitivity estimates.

    **High Sensitivity Arguments:**
    - Observational and modeling studies suggest that warming will reduce low-level cloud cover, especially stratocumulus clouds that reflect sunlight, amplifying warming.
    - Higher resolution models and advanced satellite observations indicate that high clouds may rise higher with warming, trapping more heat.

    **Low Sensitivity Arguments:**
    - Some researchers propose that certain cloud types might increase with warming, reflecting more sunlight and dampening the warming effect.
    - Uncertainty in modeling convection processes means that cloud feedback magnitude remains challenging to constrain precisely.

    ### 3. Ice-Albedo Feedback

    As ice and snow melt, they expose darker surfaces that absorb more solar radiation, further increasing warming.

    **Scientific Consensus:** This is a positive feedback, but its magnitude varies across different time scales and regions. Recent observations of rapid Arctic ice loss suggest this feedback may be stronger than previously estimated.

    ### 4. Tropical Lapse Rate Feedback

    Changes in the vertical temperature profile of the tropical atmosphere can affect how efficiently the Earth radiates heat to space.

    **Ongoing Debate:** While theory suggests this should be a negative feedback (dampening warming), its interaction with water vapor complicates the net effect, and some observations suggest it may be weaker than previously thought.

    ## Methodological Disagreements

    The sensitivity debate is not merely about interpretation of results but also involves disagreements about methodology:

    ### 1. Statistical Approaches

    Different statistical methods for analyzing observational data have yielded different sensitivity estimates:

    - Bayesian approaches that incorporate multiple lines of evidence tend to find higher sensitivity values.
    - Simple energy balance calculations often yield lower values but may oversimplify the climate system's complexity.
    - Disagreements about appropriate prior distributions in Bayesian analyses have significantly affected results.

    ### 2. Time Scale Considerations

    Transient Climate Response (TCR)—the warming at the time of CO2 doubling during a gradual increase—is lower than the Equilibrium Climate Sensitivity due to ocean thermal inertia. Some arguments focus on whether TCR is more policy-relevant than ECS for near-term planning.

    ### 3. Pattern Effects

    Recent research has identified "pattern effects"—the idea that the spatial pattern of sea surface temperature changes affects the planet's radiative response. This has complicated interpretation of the historical record:

    - Some studies suggest that using the historical warming pattern to estimate sensitivity may underestimate the long-term ECS.
    - The difference between historical patterns and long-term equilibrium patterns could explain some of the discrepancy between observational and model-based estimates.

    ## Recent Developments in the Debate

    Several important developments have shifted the debate in recent years:

    ### 1. Narrowing Uncertainty Range

    The IPCC's Sixth Assessment Report narrowed the likely range of climate sensitivity compared to previous assessments, ruling out both very low values (below 2°C) and some of the highest estimates (above 5°C).

    ### 2. Improved Understanding of Cloud Processes

    Advances in high-resolution modeling, machine learning approaches to cloud parametrization, and better satellite observations have improved our understanding of cloud feedbacks:

    - The CERES satellite measurements have helped constrain the Earth's energy imbalance.
    - Studies using Large Eddy Simulations have improved understanding of marine stratocumulus clouds.
    - Machine learning approaches have helped identify patterns in cloud behavior that inform sensitivity estimates.

    ### 3. Reconciling Model and Observational Estimates

    Recent work has made progress in explaining the discrepancy between some observational estimates (which tended toward lower values) and model-based estimates (which often suggested higher values):

    - Better accounting for aerosol forcing has reduced some of the apparent discrepancy.
    - Recognition of pattern effects has helped reconcile different estimation approaches.
    - Improved paleoclimate reconstructions have provided additional constraints that generally align with moderate to high sensitivity.

    ## Policy Implications

    The climate sensitivity debate has profound implications for climate policy:

    ### 1. Carbon Budgets

    The remaining carbon budget—how much more CO2 humanity can emit while limiting warming to a specific target—depends critically on climate sensitivity:

    - If sensitivity is at the lower end of the likely range, the remaining carbon budget would be larger, allowing more time for transition.
    - If sensitivity is at the higher end, carbon budgets are much tighter, requiring more urgent and ambitious mitigation.

    ### 2. Risk Assessment

    From a risk management perspective, uncertainty in climate sensitivity affects how policymakers should approach climate change:

    - Some argue that uncertainty justifies a precautionary approach, preparing for higher sensitivity values to avoid catastrophic outcomes.
    - Others suggest policies should target the most likely sensitivity values while maintaining flexibility to adjust as evidence evolves.

    ### 3. Adaptation Planning

    Infrastructure planning, agricultural strategies, and other adaptation measures must account for a range of possible warming scenarios directly tied to sensitivity estimates.

    ## Scientific Process in Action

    The climate sensitivity debate exemplifies how science progresses through:

    1. **Multiple lines of evidence:** No single study or approach is definitive; instead, multiple methods triangulate toward the truth.

    2. **Refinement of understanding:** Over time, the likely range has narrowed as methods improve and more data becomes available.

    3. **Productive disagreement:** Scientific disagreement has driven innovation in methods and data collection, improving overall understanding.

    4. **Uncertainty communication:** The field has developed sophisticated approaches to communicating uncertainty while still providing actionable information.

    ## Conclusion

    The climate sensitivity debate remains one of the most consequential scientific discussions of our time. While significant uncertainties persist, the evidence increasingly constrains the likely range between 2.5°C and 4°C for a doubling of atmospheric CO2. This range represents substantial warming with significant implications for natural and human systems.

    The debate illustrates how science handles uncertainty—not by claiming perfect knowledge, but by rigorously characterizing what we know, what we don't know, and the relative likelihood of different possibilities. As research continues, our understanding of climate sensitivity will further improve, helping to guide effective climate policy in the face of uncertainty.

    What remains clear despite the ongoing debate is that even at the lower end of the likely sensitivity range, unmitigated greenhouse gas emissions would lead to substantial warming with severe consequences for human societies and natural ecosystems. The debate centers not on whether human-caused climate change is real or serious, but rather on precisely how much warming will result from our emissions—a question of magnitude rather than direction.

    ## References

    This document synthesizes arguments from the scientific literature but does not cite specific papers. For detailed references on climate sensitivity research, readers are encouraged to consult the latest IPCC Assessment Report and recent peer-reviewed literature in journals such as Nature Climate Change, Journal of Climate, Geophysical Research Letters, and Proceedings of the National Academy of Sciences."""



if __name__ == "__main__":
    chat=TestRAG()
    chat.chat()
    #upload_in_KB=UploadInKB(USER_ID)
    #upload_in_KB.upload_in_kb(get_text_to_upload())