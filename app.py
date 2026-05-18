import streamlit as tf
import google.generativeai as genai
from supabase import create_client, Client
import os

# 1. Configuración de API de Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)

# 2. Configuración de Conexión a la Base de Datos (Supabase)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

tf.set_page_config(page_title="Evaluador de Oratoria", page_icon="🗺️")

tf.title("🗺️ Evaluador de Oratoria para Guías de Turismo")

# Formulario para datos del alumno
nombre = tf.text_input("Nombre completo del Estudiante:")
tipo_archivo = tf.radio("¿Qué vas a evaluar?", ("Video (Completo)", "Audio (Solo voz)"))

if tipo_archivo == "Video (Completo)":
    uploaded_file = tf.file_uploader("Cargá el video", type=["mp4", "mov", "avi"])
else:
    uploaded_file = tf.file_uploader("Cargá el audio", type=["mp3", "wav", "m4a"])

if uploaded_file is not None and nombre != "":
    if tf.button("Iniciar Evaluación Pormenorizada"):
        with tf.spinner("Analizando performance..."):
            try:
                # Procesamiento con IA
                with open("temp_file", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                media_file = genai.upload_file(path="temp_file")
                
                prompt = "Analiza este archivo de un estudiante de guía de turismo..."
                model = genai.GenerativeModel(model_name="gemini-1.5-flash")
                response = model.generate_content([media_file, prompt])
                
                # MOSTRAR EN PANTALLA
                tf.success(f"¡Evaluación de {nombre} completada!")
                tf.markdown(response.text)
                
                # 3. GUARDAR EN LA BASE DE DATOS
                if supabase:
                    datos_a_guardar = {
                        "nombre_estudiante": nombre,
                        "tipo_evaluacion": tipo_archivo,
                        "devolucion": response.text
                    }
                    supabase.table("evaluaciones").insert(datos_a_guardar).execute()
                    tf.info("💾 Los resultados se guardaron en la base de datos.")
                
                genai.delete_file(media_file.name)
                
            except Exception as e:
                tf.error(f"Error: {e}")
elif nombre == "" and uploaded_file is not None:
    tf.warning("Por favor, ingresá el nombre del estudiante antes de continuar.")
