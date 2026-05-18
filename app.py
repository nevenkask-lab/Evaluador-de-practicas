import streamlit as tf
import google.generativeai as genai
from supabase import create_client, Client
import os
import mimetypes  # Librería para detectar el tipo de archivo

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
                # 1. Detectar el tipo de archivo (MIME type) real
                mime_actual, _ = mimetypes.guess_type(uploaded_file.name)
                if not mime_actual:
                    # Forzar un tipo genérico si no lo detecta
                    mime_actual = "video/mp4" if tipo_archivo == "Video (Completo)" else "audio/mp3"

                # 2. Guardar temporalmente el archivo
                with open("temp_file", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # 3. Subir a Gemini especificando el MIME type correcto
                media_file = genai.upload_file(path="temp_file", mime_type=mime_actual)
                
                # Instrucciones detalladas para la IA
                prompt = """
                Analiza este archivo de un estudiante de guía de turismo. Ofrece una devolución pormenorizada estructurada exactamente con los siguientes títulos en Markdown:
                
                ### 📊 Resumen Ejecutivo de la Performance
                (Breve introducción de cómo lo hizo)
                
                ### 🗣️ 1. Coherencia, Cohesión y Errores del Lenguaje
                (Analiza la estructura del discurso, conectores, vocabulario técnico y presencia de muletillas)
                
                ### 🎙️ 2. Cualidades de la Voz (Oratoria)
                (Analiza minuciosamente: Dicción, Entonación, Ritmo, Pausas, Volumen e Inflexiones)
                
                ### 🧍 3. Expresión Corporal y Gestualidad (Si es video)
                (Analiza la postura, contacto visual, uso de las manos y expresión facial. Si es solo audio, indica que no aplica)
                
                ### 🎯 4. Conclusiones y Plan de Acción de Mejora
                (Da 3 consejos prácticos específicos basados en lo observado para que el alumno practique)
                """
                
                model = genai.GenerativeModel(model_name="gemini-1.5-flash")
                response = model.generate_content([media_file, prompt])
                
                # MOSTRAR EN PANTALLA
                tf.success(f"¡Evaluación de {nombre} completada!")
                tf.markdown(response.text)
                
                # 4. GUARDAR EN LA BASE DE DATOS
                if supabase:
                    datos_a_guardar = {
                        "nombre_estudiante": nombre,
                        "tipo_evaluacion": tipo_archivo,
                        "devolucion": response.text
                    }
                    supabase.table("evaluaciones").insert(datos_a_guardar).execute()
                    tf.info("💾 Los resultados se guardaron en la base de datos.")
                
                # Limpiar archivo en los servidores de Google
                genai.delete_file(media_file.name)
                
            except Exception as e:
                tf.error(f"Error durante el análisis: {e}")
elif nombre == "" and uploaded_file is not None:
    tf.warning("Por favor, ingresá el nombre del estudiante antes de continuar.")
