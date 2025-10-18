"""
RAG Chat Interface con Streamlit
Interfaz sencilla para consultar la base de datos vectorial ChromaDB
"""

import streamlit as st
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough


# CONFIGURACIÓN DE LA PÁGINA

st.set_page_config(
    page_title="RAG Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

#st.title("💬 RAG Chat - Celsia")
st.markdown("<h1 style='text-align: center;'>💬 RAG Chat - Gemma 3 4B</h1>", unsafe_allow_html=True)
st.write("Haz preguntas sobre los documentos cargados")


# INICIALIZAR SESIÓN


if "messages" not in st.session_state:
    st.session_state.messages = []

if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None

if "rag_chain" not in st.session_state:
    st.session_state.rag_chain = None


# CARGAR VECTORSTORE

@st.cache_resource
def cargar_rag():
    """Carga el vectorstore y la cadena RAG"""
    
    with st.spinner("⏳ Cargando base de datos vectorial..."):
        # Embeddings
        embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url="http://localhost:11434"
        )
        
        # Cargar vectorstore desde ChromaDB
        vectorstore = Chroma(
            persist_directory="./chromadb_storage",
            embedding_function=embeddings,
            collection_name="rag_collection"
        )
        
        # LLM
        llm = OllamaLLM(
            model="gemma3:4b",
            base_url="http://localhost:11434",
            temperature=0.7
        )
        
        # Retriever
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )
        
        # Prompt
        prompt_template = """**[INSTRUCCIONES CLAVE ZERO-SHOT Y LIMITACIÓN DE FUENTE]**
Tu ÚNICA tarea es responder a la **PREGUNTA** del usuario, utilizando EXCLUSIVAMENTE la información que se encuentra en el **CONTEXTO** proporcionado a continuación.

**REGLAS ESTRICTAS para evitar alucinaciones:**
1.  **SI** la respuesta a la PREGUNTA se encuentra explícita o implícitamente en el **CONTEXTO**, genera una respuesta completa y profesional.
2.  **SI** no puedes encontrar la respuesta en el **CONTEXTO**, o si la información es insuficiente, debes responder **ÚNICAMENTE** con la siguiente frase predefinida: "Lamento no poder ofrecer una respuesta precisa basada en la información disponible. Por favor, consulta los canales oficiales de CELSIA o llama a la línea de servicio al cliente."
3.  **NUNCA** utilices tu conocimiento general o información que no esté en el **CONTEXTO**. **NUNCA** inventes tarifas, fechas o procesos.
Coloca el cursor sobre un mensaje para fijarlo
        
Contexto:
{context}

Pregunta: {question}

Respuesta:"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Cadena RAG
        def formato_docs(docs):
            return "\n\n".join([doc.page_content for doc in docs])
        
        rag_chain = (
            {"context": retriever | formato_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
        )
        
        return vectorstore, rag_chain, retriever

# Cargar RAG
vectorstore, rag_chain, retriever = cargar_rag()

st.success("✅ Base de datos cargada correctamente")

# SIDEBAR

with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Info
    st.info(f"📊 Documentos en la BD: {vectorstore._collection.count()}")
    
    # Botón para limpiar historial
    if st.button("🗑️ Limpiar historial"):
        st.session_state.messages = []
        st.rerun()
    
    # Información
    st.divider()
    st.subheader("ℹ️ Información")
    st.write("""
    - **Modelo LLM**: Gemma 3 4B
    - **Embeddings**: nomic-embed-text
    - **Base de datos**: ChromaDB
    - **Framework**: LangChain
    """)

# MOSTRAR HISTORIAL DE MENSAJES

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ENTRADA DEL USUARIO

pregunta = st.chat_input("Escribe tu pregunta...")

if pregunta:
    # Agregar pregunta al historial
    st.session_state.messages.append({"role": "user", "content": pregunta})
    
    with st.chat_message("user"):
        st.markdown(pregunta)
    
    # Generar respuesta
    with st.chat_message("assistant"):
        with st.spinner("⏳ Pensando..."):
            # Obtener respuesta
            respuesta = rag_chain.invoke(pregunta)
            
            # Mostrar respuesta
            st.markdown(respuesta)
            
            # Agregar al historial
            st.session_state.messages.append({
                "role": "assistant",
                "content": respuesta
            })
            
            # Mostrar documentos recuperados en expander
            with st.expander("📚 Documentos recuperados"):
                docs = retriever.invoke(pregunta)
                for i, doc in enumerate(docs, 1):
                    st.write(f"**[{i}] {doc.metadata['source']}**")
                    st.info(doc.page_content)