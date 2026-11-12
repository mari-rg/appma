import json
import platform
import time
import paho.mqtt.client as paho
import streamlit as st

# Configuración de la página (si ya la tienes en Inicio.py, puedes quitar este bloque)
st.set_page_config(
    page_title="Control de la Casa | Smart Home",
    page_icon="🏠",
    layout="centered",
)

# Estilos CSS para darle apariencia de panel de hogar inteligente
st.markdown(
    """
    <style>
    .main-header {
        text-align: center;
        padding: 0.5rem 0 0.5rem 0;
    }
    .status-badge {
        display: inline-block;
        background-color: rgba(46, 204, 113, 0.15);
        color: #2ecc71;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid rgba(46, 204, 113, 0.4);
    }
    div.stButton > button {
        border-radius: 10px;
        height: 3em;
        font-weight: 600;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Parámetros de conexión MQTT (intactos)
BROKER = "broker.mqttdashboard.com"
PORT = 1883


def on_publish(client, userdata, result):
  print("El dato ha sido publicado \n")


def on_message(client, userdata, message):
  global message_received
  time.sleep(2)
  message_received = str(message.payload.decode("utf-8"))
  st.write(message_received)


def enviar_comando_hogar(client_id, topico, payload_dict):
  client = paho.Client(client_id)
  client.on_publish = on_publish
  client.connect(BROKER, PORT)
  mensaje = json.dumps(payload_dict)
  client.publish(topico, mensaje)
  client.disconnect()


# Estados visuales iniciales de la casa
if "estado_puerta" not in st.session_state:
  st.session_state.estado_puerta = "En espera de orden"
if "estado_luces" not in st.session_state:
  st.session_state.estado_luces = "En espera de orden"

# Encabezado principal estilo Smart Home
st.markdown(
    """
    <div class="main-header">
        <h1>🏠 CONTROL DE LA CASA</h1>
        <p style="color: gray; margin-top: -10px;">Panel de automatización y control inteligente del hogar</p>
        <span class="status-badge">● Hogar conectado</span>
    </div>
""",
    unsafe_allow_html=True,
)

st.divider()

# --- ZONA 1: ACCESO PRINCIPAL ---
with st.container(border=True):
  st.subheader("🚪 Acceso Principal")
  estado_puerta_texto = st.empty()

  col1, col2 = st.columns(2)
  with col1:
    if st.button("🔓 Abrir puerta", use_container_width=True):
      enviar_comando_hogar(
          "GIT-majoo", "voice_Majooo", {"Act1": "abre la puerta"}
      )
      st.session_state.estado_puerta = "Puerta principal abierta"
      st.toast("Orden enviada: Puerta abierta", icon="🔓")

  with col2:
    if st.button("🔒 Cerrar puerta", use_container_width=True):
      enviar_comando_hogar(
          "GIT-majoo", "voice_Majooo", {"Act1": "Cierra la puerta"}
      )
      st.session_state.estado_puerta = "Puerta principal cerrada"
      st.toast("Orden enviada: Puerta cerrada", icon="🔒")

  estado_puerta_texto.caption(
      f"Última acción: **{st.session_state.estado_puerta}**"
  )

# --- ZONA 2: ILUMINACIÓN ---
with st.container(border=True):
  st.subheader("💡 Iluminación del Hogar")
  estado_luces_texto = st.empty()

  col3, col4 = st.columns(2)
  with col3:
    if st.button("☀️ Encender luces", use_container_width=True):
      enviar_comando_hogar(
          "GIT-majoo", "voice_Majooo", {"Act1": "enciende las luces"}
      )
      st.session_state.estado_luces = "Luces encendidas"
      st.toast("Orden enviada: Luces encendidas", icon="💡")

  with col4:
    if st.button("🌙 Apagar luces", use_container_width=True):
      enviar_comando_hogar(
          "GIT-majoo", "voice_Majooo", {"Act1": "apaga las luces"}
      )
      st.session_state.estado_luces = "Luces apagadas"
      st.toast("Orden enviada: Luces apagadas", icon="🌙")

  estado_luces_texto.caption(
      f"Última acción: **{st.session_state.estado_luces}**"
  )

# --- ZONA 3: REGULACIÓN ANALÓGICA ---
with st.container(border=True):
  st.subheader("🎚️ Regulación de Ambiente")
  st.caption(
      "Ajusta el nivel porcentual (intensidad de iluminación, apertura de"
      " persianas o climatización)"
  )

  values = st.slider(
      "Nivel deseado (%)",
      min_value=0.0,
      max_value=100.0,
      value=0.0,
      format="%.0f%%",
  )

  if st.button(
      "📡 Aplicar ajuste en la casa", use_container_width=True, type="primary"
  ):
    enviar_comando_hogar("GIT-HUB", "cmqtt_a", {"Analog": float(values)})
    st.success(f"✅ Ajuste aplicado al {values:.0f}% en el sistema del hogar.")

# Detalle técnico discreto en la barra lateral
with st.sidebar:
  st.divider()
  st.caption(f"⚙️ Núcleo activo | Python {platform.python_version()}")
