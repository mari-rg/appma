import base64
import html
import json
import platform
import random
import re
import time
import unicodedata
from pathlib import Path

import paho.mqtt.client as paho
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Mansión Embrujada · MQTT", page_icon="🦇", layout="wide")

# ───────────── CONFIGURACIÓN ─────────────
BROKER, PORT = "broker.mqttdashboard.com", 1883
TOPIC_VOZ, TOPIC_ANALOG = "voice_Majooo", "cmqtt_a"
WOKWI_URL = "https://wokwi.com/projects/479874106123681793"
RAIZ = Path(__file__).resolve().parent.parent
# imagen de fondo: la busca en static/fondo.jpg y, si no está, en la raíz del repo (fondo.jpg)
FONDO = next((f for f in (RAIZ / "static" / "fondo.jpg", RAIZ / "fondo.jpg") if f.exists()), RAIZ / "static" / "fondo.jpg")

# Sonidos (sube los 4 .mp3 a la raíz del repo, junto a fondo.jpg)
SONIDOS = {
    "puerta_abre": "sonido_1.mp3",
    "puerta_cierra": "sonido_2.mp3",
    "luz_on": "sonido_3.mp3",
    "luz_off": "sonido_4.mp3",
}
SONIDO_DE_COMANDO = {
    "abre la puerta": "puerta_abre",
    "Cierra la puerta": "puerta_cierra",
    "enciende las luces": "luz_on",
    "apaga las luces": "luz_off",
}

# ───────────── ESTADO ─────────────
ss = st.session_state
ss.setdefault("puerta", "cerrada")
ss.setdefault("luces", False)
ss.setdefault("valor", 0.0)
ss.setdefault("log", [])
ss.setdefault("voz_msg", "")
ss.setdefault("sonido", None)


def publicar(topic, payload):
    """Publica un mensaje JSON en el broker MQTT. Devuelve True si salió bien."""
    msg, ok = json.dumps(payload), True
    try:
        try:
            cli = paho.Client(paho.CallbackAPIVersion.VERSION1, "GIT-majoo")  # paho 2.x
        except AttributeError:
            cli = paho.Client("GIT-majoo")  # paho 1.x
        cli.connect(BROKER, PORT, 60)
        cli.loop_start()
        cli.publish(topic, msg).wait_for_publish(timeout=5)
        cli.loop_stop()
        cli.disconnect()
    except Exception:
        ok = False
    ss.log = [(time.strftime("%H:%M:%S"), topic, msg, ok)] + ss.log[:7]
    st.toast("🦇 Hechizo enviado" if ok else "💀 El hechizo falló (¿broker?)")
    return ok


def comando(texto, **estado):
    if publicar(TOPIC_VOZ, {"Act1": texto}):
        ss.update(estado)
        ss.sonido = SONIDO_DE_COMANDO.get(texto)  # suena solo si el mensaje salió bien


def enviar_analogico():
    publicar(TOPIC_ANALOG, {"Analog": float(ss.valor)})


def interpretar(texto):
    """Convierte una frase libre en el comando EXACTO que entiende el ESP32 de Wokwi."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    if re.search(r"puerta|portal", t):
        if re.search(r"\b(abre|abrir|abra|abrela|abreme)\b", t):
            return "abre la puerta", {"puerta": "abierta"}
        if re.search(r"\b(cierra|cerrar|cierre|cierrala|cierrame)\b", t):
            return "Cierra la puerta", {"puerta": "cerrada"}
    if re.search(r"\bluz\b|luces|ventana|lampara", t):
        if re.search(r"\b(apaga|apagar|apague|apagala|apagame)\b", t):
            return "apaga las luces", {"luces": False}
        if re.search(r"\b(enciende|encender|prende|prender|prendela|enciendela|activa)\b", t):
            return "enciende las luces", {"luces": True}
    return None, {}


def procesar_voz():
    texto = ss.voz_txt.strip()
    ss.voz_txt = ""  # se limpia para poder repetir la misma frase
    if not texto:
        return
    cmd, estado = interpretar(texto)
    seguro = html.escape(texto)
    if cmd:
        ss.voz_msg = f"🎙️ «{seguro}» → <b>{cmd}</b>"
        comando(cmd, **estado)
    else:
        ss.voz_msg = f"🎙️ «{seguro}» → no reconocí ese hechizo (prueba: abre/cierra la puerta, enciende/apaga las luces)"


MIC_HTML = """
<style>
body{margin:0;font-family:Quicksand,sans-serif;color:#f6eaff;display:flex;align-items:center;gap:16px;height:96px}
button{width:76px;height:76px;border-radius:50%;border:2px solid #ffb347;background:radial-gradient(circle,#7a3f94,#3b1750);font-size:32px;cursor:pointer;color:#fff;box-shadow:0 0 18px rgba(255,179,71,.5);flex:none}
button.on{animation:p 1s infinite;box-shadow:0 0 34px 8px #ffb347}
@keyframes p{50%{transform:scale(1.1)}}
#s{font-size:.95rem}
</style>
<button id="m">🎙️</button><div id="s">Pulsa el micrófono y di: «abre la puerta»…</div>
<script>
const P=window.parent,S=document.getElementById('s'),B=document.getElementById('m');
const SR=P.SpeechRecognition||P.webkitSpeechRecognition||window.SpeechRecognition||window.webkitSpeechRecognition;
function enviar(t){
  const inp=[...P.document.querySelectorAll('input')].find(i=>i.getAttribute('aria-label')==='Hechizo de voz o texto');
  if(!inp){S.textContent='No encontré el campo de texto';return;}
  const set=Object.getOwnPropertyDescriptor(P.HTMLInputElement.prototype,'value').set;
  inp.focus();set.call(inp,t);
  inp.dispatchEvent(new Event('input',{bubbles:true}));
  ['keydown','keypress','keyup'].forEach(k=>inp.dispatchEvent(new KeyboardEvent(k,{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true})));
  inp.blur();
}
if(!SR){S.textContent='Tu navegador no soporta voz (usa Chrome o Edge). Puedes escribir el hechizo abajo.';B.disabled=true;}
else{
  const r=new SR();r.lang='es-CO';r.interimResults=false;r.maxAlternatives=1;
  r.onstart=()=>{B.classList.add('on');S.textContent='Escuchando…';};
  r.onend=()=>B.classList.remove('on');
  r.onerror=e=>{S.textContent='Error de micrófono: '+e.error;};
  r.onresult=e=>{const t=e.results[0][0].transcript;S.textContent='Escuché: «'+t+'»';enviar(t);};
  B.onclick=()=>{try{r.start();}catch(_){}};
}
</script>
"""


@st.cache_data
def sonido_b64(nombre):
    for ruta in (RAIZ / nombre, RAIZ / "sonidos" / nombre, RAIZ / "static" / nombre):
        if ruta.exists():
            return base64.b64encode(ruta.read_bytes()).decode()
    return None


JS_SONIDO = """<script>
const P=window.parent, K='__CLAVE__';  // __N__
if(K==='luz_on'||K==='luz_off'){ if(P.__luz){P.__luz.pause();P.__luz=null;} }
const A=new P.Audio('data:audio/mpeg;base64,__B64__');
if(K==='luz_on'){P.__luz=A;}
A.play().catch(()=>{});
</script>"""


def reproducir(clave):
    b64 = sonido_b64(SONIDOS[clave])
    if b64:
        js = JS_SONIDO.replace("__CLAVE__", clave).replace("__N__", str(time.time_ns())).replace("__B64__", b64)
        components.html(js, height=0)


@st.cache_data
def fondo_css():
    if FONDO.exists():
        b64 = base64.b64encode(FONDO.read_bytes()).decode()
        return f"url(data:image/jpeg;base64,{b64})"
    return "radial-gradient(ellipse at 50% 20%,#8b3fa8,#2a0f3d 60%,#0d0415)"


# ───────────── ESTILOS + MURCIÉLAGOS ─────────────
random.seed(13)
murcielagos = "".join(
    f'<span class="bat" style="top:{random.randint(4,60)}%;font-size:{random.randint(16,34)}px;'
    f'animation-delay:-{random.uniform(0,30):.1f}s;animation-duration:{random.uniform(14,30):.1f}s">🦇</span>'
    for _ in range(9)
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Creepster&family=Cinzel:wght@600;800&family=Quicksand:wght@400;600&display=swap');
:root{--p:#622e74;--m:#c86bff;--c:#f3f0c8;--g:#ffb347;}
html,body{background:__BG__ center/cover fixed no-repeat;}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:transparent !important;}
.stApp,.stApp p,.stApp label,.stApp span,.stApp li{font-family:'Quicksand',sans-serif;color:#f6eaff;}
.velo{position:fixed;inset:0;z-index:-1;background:linear-gradient(180deg,rgba(15,4,25,.25),rgba(15,4,25,.7));}
.bat{position:fixed;left:-60px;z-index:0;pointer-events:none;filter:drop-shadow(0 0 6px #000);animation:vuelo linear infinite;}
@keyframes vuelo{0%{transform:translate(0,0) scaleX(1)}25%{transform:translate(30vw,-40px)}50%{transform:translate(60vw,30px)}75%{transform:translate(90vw,-30px)}100%{transform:translate(120vw,10px)}}
.hero{text-align:center;padding:1rem 0 .5rem}
.hero h1{font-family:'Creepster',cursive;font-weight:400;letter-spacing:.06em;font-size:clamp(2.8rem,7vw,5.4rem);margin:.2rem 0;color:var(--c) !important;text-shadow:0 0 14px var(--g),0 0 40px var(--m),0 4px 0 #2a0f3d;animation:titila 5s infinite;}
@keyframes titila{0%,92%,100%{opacity:1}94%{opacity:.55}96%{opacity:1}98%{opacity:.7}}
.hero p{opacity:.92;font-size:1.1rem;text-shadow:0 2px 8px #000}
.chip{display:inline-block;margin:.25rem;padding:.35rem .9rem;border-radius:99px;border:1px solid rgba(255,255,255,.3);background:rgba(20,6,30,.6);color:#fff !important;text-decoration:none;font-size:.85rem;backdrop-filter:blur(8px);}
a.chip:hover{background:var(--g);color:#1b0b27 !important;box-shadow:0 0 18px var(--g)}
div[data-testid="column"],div[data-testid="stColumn"],.col{background:rgba(24,8,36,.66);backdrop-filter:blur(12px);border:1px solid rgba(200,107,255,.35);border-radius:22px;padding:1.2rem 1.3rem;box-shadow:0 10px 40px rgba(0,0,0,.5);}
h3{font-family:'Cinzel',serif !important;font-weight:800;text-align:center;color:var(--g) !important;text-shadow:0 0 10px rgba(255,179,71,.5);}
.stButton>button,.btn{width:100%;border-radius:14px;border:1px solid var(--g);background:linear-gradient(135deg,rgba(98,46,116,.95),rgba(255,179,71,.25));color:#fff;font-weight:600;transition:.25s;font-family:inherit;}
.stButton>button:hover,.btn:hover{transform:translateY(-2px);box-shadow:0 0 22px var(--g);border-color:var(--c);color:#fff}
.escena{display:flex;justify-content:center;align-items:flex-end;height:210px;margin-bottom:.8rem}
.arco{position:relative;width:120px;height:180px;border-radius:60px 60px 0 0;border:5px solid #3a1c4d;border-bottom:none;background:#0b0312;perspective:700px;box-shadow:0 0 0 3px #7a4a9a}
.arco .dentro{position:absolute;inset:0;border-radius:55px 55px 0 0;opacity:0;transition:opacity 1s;background:radial-gradient(circle at 50% 70%,#fff6c8 0%,#ffcf5a 35%,#ff9b3d 70%,#7a2f10 100%);}
.hoja{position:absolute;inset:0;border-radius:55px 55px 0 0;transform-origin:left center;transition:transform 1.1s cubic-bezier(.6,0,.2,1);background:repeating-linear-gradient(90deg,#4a2a17 0 14px,#3a1f10 14px 16px);border-right:3px solid #1d0f07;}
.hoja::after{content:"";position:absolute;right:14px;top:55%;width:10px;height:10px;border-radius:50%;background:var(--g);box-shadow:0 0 8px var(--g)}
.abierta .hoja{transform:rotateY(-105deg)}
.abierta .dentro{opacity:1;animation:pulso 2s ease-in-out infinite}
.ventana{display:flex;flex-direction:column;align-items:center}
.vidrio{width:100px;height:140px;border-radius:50px 50px 4px 4px;background:#1a0a26;border:5px solid #3a1c4d;transition:.5s;position:relative}
.vidrio::before{content:"";position:absolute;left:50%;top:0;bottom:0;width:4px;background:#3a1c4d;transform:translateX(-50%)}
.vidrio::after{content:"";position:absolute;top:55%;left:0;right:0;height:4px;background:#3a1c4d}
.alfeizar{width:124px;height:12px;border-radius:4px;background:#3a1c4d}
.on .vidrio{background:radial-gradient(circle at 50% 60%,#fff6c8,#ffcf5a 55%,#ff9b3d);box-shadow:0 0 40px 14px rgba(255,179,71,.7),0 0 110px 36px rgba(200,107,255,.35);animation:pulso 1.8s ease-in-out infinite}
@keyframes pulso{50%{filter:brightness(1.22)}}
.gauge{--v:0;width:176px;height:176px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--g) calc(var(--v)*3.6deg),rgba(255,255,255,.14) 0);box-shadow:0 0 calc(8px + var(--v)*.5px) var(--c);transition:.4s}
.gauge div{width:140px;height:140px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#fffdea,#d9d5a8 60%,#a29d73);display:grid;place-items:center;font-family:'Cinzel',serif;font-weight:800;font-size:2.1rem;color:#3b1750;box-shadow:inset -10px -8px 22px rgba(60,40,80,.45)}
.estado{text-align:center;font-size:.9rem;opacity:.95;margin-bottom:.6rem}
.grim{margin-top:1.2rem;padding:1rem 1.4rem;border-radius:20px;background:rgba(12,3,20,.78);border:1px solid rgba(200,107,255,.3);font-family:ui-monospace,monospace;font-size:.82rem}
.grim b{color:var(--g)} .bien{color:#7dffb0} .mal{color:#ff7d7d}
</style>
"""
st.markdown(
    CSS.replace("__BG__", fondo_css()) + '<div class="velo"></div>' + murcielagos,
    unsafe_allow_html=True,
)

# ───────────── CABECERA ─────────────
st.markdown(
    f"""<div class="hero"><div class="chip">🦇 IoT · MQTT · Wokwi</div>
<h1>Mansión Embrujada</h1><p>Abre portales, enciende ventanas y despierta la luna desde el más allá</p>
<span class="chip">📡 {BROKER}</span><span class="chip">🗝️ {TOPIC_VOZ}</span><span class="chip">🌕 {TOPIC_ANALOG}</span>
<a class="chip" href="{WOKWI_URL}" target="_blank">🧪 Abrir circuito en Wokwi</a></div>""",
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3, gap="large")

# ───────────── PUERTA ─────────────
with col1:
    st.markdown("### 🚪 El Portal")
    abierta = ss.puerta == "abierta"
    st.markdown(
        f'<div class="escena"><div class="arco {"abierta" if abierta else ""}"><div class="dentro"></div><div class="hoja"></div></div></div>'
        f'<div class="estado">La puerta está <b>{ss.puerta}</b></div>',
        unsafe_allow_html=True,
    )
    st.button("🌀 Abrir la puerta", on_click=comando, args=("abre la puerta",), kwargs={"puerta": "abierta"}, key="b1")
    st.button("🔒 Cerrar la puerta", on_click=comando, args=("Cierra la puerta",), kwargs={"puerta": "cerrada"}, key="b2")

# ───────────── LUCES ─────────────
with col2:
    st.markdown("### 🕯️ Las Ventanas")
    st.markdown(
        f'<div class="escena"><div class="ventana {"on" if ss.luces else ""}"><div class="vidrio"></div><div class="alfeizar"></div></div></div>'
        f'<div class="estado">Las luces están <b>{"encendidas" if ss.luces else "apagadas"}</b></div>',
        unsafe_allow_html=True,
    )
    st.button("🕯️ Encender las luces", on_click=comando, args=("enciende las luces",), kwargs={"luces": True}, key="b3")
    st.button("🌑 Apagar las luces", on_click=comando, args=("apaga las luces",), kwargs={"luces": False}, key="b4")

# ───────────── ANALÓGICO ─────────────
with col3:
    st.markdown("### 🌕 La Luna")
    st.slider("Energía lunar", 0.0, 100.0, key="valor")
    st.markdown(
        f'<div class="escena" style="align-items:center"><div class="gauge" style="--v:{ss.valor}"><div>{ss.valor:.0f}</div></div></div>',
        unsafe_allow_html=True,
    )
    st.button("🌕 Enviar valor analógico", on_click=enviar_analogico, key="b5")

# ───────────── ORÁCULO (VOZ) ─────────────
(orc,) = st.columns(1)
with orc:
    st.markdown("### 🎙️ El Oráculo")
    components.html(MIC_HTML, height=100)
    st.text_input(
        "Hechizo de voz o texto",
        key="voz_txt",
        on_change=procesar_voz,
        placeholder="Di o escribe: «abre la puerta», «apaga las luces»…",
    )
    if ss.voz_msg:
        st.markdown(f'<div class="estado">{ss.voz_msg}</div>', unsafe_allow_html=True)

# ───────────── GRIMORIO ─────────────
filas = "".join(
    f'<div><b>{h}</b> → {t} <span class="{"bien" if ok else "mal"}">{"✔" if ok else "✘"}</span> {m}</div>'
    for h, t, m, ok in ss.log
) or "<div>Aún no has lanzado ningún hechizo…</div>"
st.markdown(f'<div class="grim">📜 <b>Grimorio de transmisiones</b>{filas}</div>', unsafe_allow_html=True)

if ss.sonido:
    reproducir(ss.sonido)
    ss.sonido = None

with st.expander("Detalles técnicos"):
    st.write("Versión de Python:", platform.python_version())
