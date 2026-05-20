import streamlit as tf
from google import genai
from supabase import create_client, Client
import os
import mimetypes
import time  # Necesario para las esperas de tiempo

# 1. Configuración de API de Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
client_gemini = genai.Client(api_key=GENAI_API_KEY) if GENAI_API_KEY else None

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
        if not client_gemini:
            tf.error("Falta configurar la API Key de Gemini en los Secrets de Streamlit.")
        else:
            try:
                # 1. Detectar el tipo de archivo (MIME type) real
                mime_actual, _ = mimetypes.guess_type(uploaded_file.name)
                if not mime_actual:
                    mime_actual = "video/mp4" if tipo_archivo == "Video (Completo)" else "audio/mp3"

                # 2. Guardar temporalmente el archivo localmente
                with open("temp_file", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # 3. Subir a Gemini usando el gestor de archivos
                media_file = client_gemini.files.upload(file="temp_file", config={"mime_type": mime_actual})
                
                # Esperar a que el archivo esté ACTIVE en los servidores de Google
                with tf.spinner("Google está procesando el archivo para la IA..."):
                    while media_file.state.name == "PROCESSING":
                        time.sleep(2)
                        media_file = client_gemini.files.get(name=media_file.name)
                    
                    if media_file.state.name == "FAILED":
                        raise Exception("El procesamiento del archivo falló en los servidores de Google.")

                # 4. Definir las instrucciones detalladas para la IA (El Prompt)
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
                
                # 5. Llamada al modelo con lógica de reintento automático por alta demanda
                with tf.spinner("Analizando performance minuciosamente..."):
                    max_intentos = 3
                    response = None
                    for intento in range(max_intentos):
                        try:
                            response = client_gemini.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=[media_file, prompt]
                            )
                            break
                        except Exception as e:
                            if "503" in str(e) or "UNAVAILABLE" in str(e).upper():
                                if intento < max_intentos - 1:
                                    time.sleep(3)
                                    continue
                            raise e
                
                # MOSTRAR EN PANTALLA
                if response:
                    tf.success(f"¡Evaluación de {nombre} completada!")
                    tf.markdown(response.text)
                    
                    # 6. GUARDAR EN LA BASE DE DATOS
                    if supabase:
                        datos_a_guardar = {
                            "nombre_estudiante": nombre,
                            "tipo_evaluacion": tipo_archivo,
                            "devolucion": response.text
                        }
                        supabase.table("evaluaciones").insert(datos_a_guardar).execute()
                        tf.info("💾 Los resultados se guardaron en la base de datos.")
                
                # Limpiar el archivo de los servidores de Google
                client_gemini.files.delete(name=media_file.name)
                
            except Exception as e:
                tf.error(f"Error durante el análisis: {e}")
                    
elif nombre == "" and uploaded_file is not None:
    tf.warning("Por favor, ingresá el nombre del estudiante antes de continuar.")
